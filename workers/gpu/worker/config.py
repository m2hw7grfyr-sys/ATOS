from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class WorkerConfig:
    main_url: str
    api_key: str
    worker_id: str
    worker_name: str
    worker_type: str
    ollama_url: str
    model_name: str
    heartbeat_interval_seconds: int
    poll_interval_seconds: int
    request_timeout_seconds: int
    generation_timeout_seconds: int
    supported_models: list[str]
    log_level: str

    @classmethod
    def load(cls, config_path: str | None = None) -> "WorkerConfig":
        if config_path:
            _load_env_file(Path(config_path))
        default_id = f"gpu-{socket.gethostname()}"
        model = os.environ.get("MODEL_NAME", "llama3.1:8b")
        supported = [
            item.strip()
            for item in os.environ.get("SUPPORTED_MODELS", model).split(",")
            if item.strip()
        ]
        return cls(
            main_url=os.environ.get("MAIN_URL", "http://127.0.0.1:8080").rstrip("/"),
            api_key=os.environ.get("GPU_WORKER_API_KEY", ""),
            worker_id=os.environ.get("WORKER_ID", default_id),
            worker_name=os.environ.get("WORKER_NAME", default_id),
            worker_type=os.environ.get("WORKER_TYPE", "gpu"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
            model_name=model,
            heartbeat_interval_seconds=_int_env("HEARTBEAT_INTERVAL_SECONDS", 10),
            poll_interval_seconds=_int_env("POLL_INTERVAL_SECONDS", 5),
            request_timeout_seconds=_int_env("REQUEST_TIMEOUT_SECONDS", 60),
            generation_timeout_seconds=_int_env("GENERATION_TIMEOUT_SECONDS", 900),
            supported_models=supported,
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.main_url:
            errors.append("MAIN_URL is required")
        if not self.api_key:
            errors.append("GPU_WORKER_API_KEY is required")
        if not self.ollama_url:
            errors.append("OLLAMA_URL is required")
        if not self.model_name:
            errors.append("MODEL_NAME is required")
        return errors


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:6]}...{value[-4:]}"
