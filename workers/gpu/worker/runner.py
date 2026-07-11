from __future__ import annotations

import logging
import signal
import threading
import time
from dataclasses import dataclass
from typing import Any

from .config import WorkerConfig, mask_secret
from .http_json import HttpJsonError
from .main_client import MainClient
from .ollama_client import OllamaClient

LOGGER = logging.getLogger("atos.gpu_worker")


@dataclass
class RuntimeState:
    status: str = "idle"
    current_task_id: int | None = None
    last_error: str | None = None
    stop_requested: bool = False


class GPUWorker:
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.main = MainClient(config)
        self.ollama = OllamaClient(config)
        self.state = RuntimeState()
        self._lock = threading.Lock()

    def status_payload(self) -> dict[str, Any]:
        with self._lock:
            version = self.ollama.version()
            return {
                "status": self.state.status,
                "version": "gpu-worker-v0.1",
                "ollama_reachable": bool(version),
                "ollama_version": version,
                "model_name": self.config.model_name,
                "current_task_id": self.state.current_task_id,
                "last_error": self.state.last_error,
            }

    def heartbeat_loop(self) -> None:
        while not self.state.stop_requested:
            try:
                self.main.heartbeat(self.status_payload())
                LOGGER.info("heartbeat sent", extra={"worker_id": self.config.worker_id, "action": "heartbeat", "result": "ok"})
            except Exception as exc:
                LOGGER.warning("heartbeat failed: %s", exc, extra={"worker_id": self.config.worker_id, "action": "heartbeat", "result": "failed"})
            time.sleep(self.config.heartbeat_interval_seconds)

    def start_heartbeat(self) -> threading.Thread:
        thread = threading.Thread(target=self.heartbeat_loop, name="gpu-heartbeat", daemon=True)
        thread.start()
        return thread

    def check_ready(self) -> list[str]:
        errors = self.config.validate()
        if not self.ollama.version():
            errors.append("Ollama API is not reachable")
        elif not self.ollama.model_available(self.config.model_name):
            errors.append(f"Model is not available: {self.config.model_name}")
        return errors

    def run_once(self) -> bool:
        task = self.main.lease_task()
        if not task:
            return False
        task_id = int(task["id"])
        with self._lock:
            self.state.status = "working"
            self.state.current_task_id = task_id
            self.state.last_error = None
        try:
            self.main.mark_started(task_id)
            LOGGER.info("task started", extra={"worker_id": self.config.worker_id, "task_id": task_id, "action": "started"})
            result_text, metrics = self.ollama.generate(
                str(task.get("prompt") or ""),
                task.get("system_prompt"),
                task.get("model") or self.config.model_name,
                task.get("options") or {},
            )
            self.main.complete_task(task_id, result_text, metrics)
            LOGGER.info("task completed", extra={"worker_id": self.config.worker_id, "task_id": task_id, "action": "complete", "result": "ok"})
        except Exception as exc:
            error_type = exc.__class__.__name__
            retryable = True
            if isinstance(exc, HttpJsonError) and 400 <= exc.status < 500:
                retryable = False
            try:
                self.main.fail_task(task_id, str(exc), error_type, retryable=retryable)
            except Exception as fail_exc:
                LOGGER.error("failed to report task failure: %s", fail_exc, extra={"worker_id": self.config.worker_id, "task_id": task_id, "action": "fail_report", "result": "failed"})
            with self._lock:
                self.state.last_error = str(exc)[:500]
            LOGGER.exception("task failed", extra={"worker_id": self.config.worker_id, "task_id": task_id, "action": "generate", "result": "failed"})
        finally:
            with self._lock:
                self.state.status = "idle"
                self.state.current_task_id = None
        return True

    def run_forever(self) -> None:
        LOGGER.info(
            "worker starting: main=%s key=%s model=%s",
            self.config.main_url,
            mask_secret(self.config.api_key),
            self.config.model_name,
            extra={"worker_id": self.config.worker_id, "action": "startup"},
        )
        self.start_heartbeat()
        backoff = self.config.poll_interval_seconds
        while not self.state.stop_requested:
            try:
                handled = self.run_once()
                backoff = self.config.poll_interval_seconds
                if not handled:
                    time.sleep(self.config.poll_interval_seconds)
            except KeyboardInterrupt:
                self.state.stop_requested = True
            except Exception as exc:
                with self._lock:
                    self.state.last_error = str(exc)[:500]
                LOGGER.warning("poll loop failed: %s", exc, extra={"worker_id": self.config.worker_id, "action": "poll", "result": "failed"})
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)


def install_signal_handlers(worker: GPUWorker) -> None:
    def _request_stop(signum: int, _frame: object) -> None:
        LOGGER.info("stop requested by signal %s", signum, extra={"worker_id": worker.config.worker_id, "action": "stop"})
        worker.state.stop_requested = True

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
