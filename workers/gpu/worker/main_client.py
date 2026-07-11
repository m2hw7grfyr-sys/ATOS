from __future__ import annotations

from typing import Any

from .config import WorkerConfig
from .http_json import request_json


class MainClient:
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.headers = {"Authorization": f"Bearer {config.api_key}"}

    def heartbeat(self, status: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "worker_id": self.config.worker_id,
            "worker_name": self.config.worker_name,
            "worker_type": self.config.worker_type,
            **status,
        }
        return request_json(
            "POST",
            f"{self.config.main_url}/api/gpu-worker/heartbeat",
            payload,
            self.headers,
            self.config.request_timeout_seconds,
        )

    def lease_task(self) -> dict[str, Any] | None:
        response = request_json(
            "POST",
            f"{self.config.main_url}/api/gpu-worker/tasks/lease",
            {"worker_id": self.config.worker_id, "supported_models": self.config.supported_models},
            self.headers,
            self.config.request_timeout_seconds,
        )
        return response.get("task")

    def mark_started(self, task_id: int) -> None:
        request_json(
            "POST",
            f"{self.config.main_url}/api/gpu-worker/tasks/{task_id}/started",
            {"worker_id": self.config.worker_id},
            self.headers,
            self.config.request_timeout_seconds,
        )

    def complete_task(self, task_id: int, result_text: str, metrics: dict[str, Any]) -> None:
        request_json(
            "POST",
            f"{self.config.main_url}/api/gpu-worker/tasks/{task_id}/complete",
            {"worker_id": self.config.worker_id, "result_text": result_text, "metrics": metrics},
            self.headers,
            self.config.request_timeout_seconds,
        )

    def fail_task(self, task_id: int, error_message: str, error_type: str, retryable: bool = True) -> None:
        request_json(
            "POST",
            f"{self.config.main_url}/api/gpu-worker/tasks/{task_id}/failed",
            {
                "worker_id": self.config.worker_id,
                "error_message": error_message[:4000],
                "error_type": error_type,
                "retryable": retryable,
            },
            self.headers,
            self.config.request_timeout_seconds,
        )
