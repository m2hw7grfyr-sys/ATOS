from __future__ import annotations

import time
from typing import Any

from .config import WorkerConfig
from .http_json import request_json


class OllamaClient:
    def __init__(self, config: WorkerConfig):
        self.config = config

    def version(self) -> str | None:
        try:
            response = request_json("GET", f"{self.config.ollama_url}/api/version", timeout=10)
            return str(response.get("version") or "")
        except Exception:
            return None

    def model_available(self, model: str | None = None) -> bool:
        try:
            response = request_json("GET", f"{self.config.ollama_url}/api/tags", timeout=10)
        except Exception:
            return False
        target = model or self.config.model_name
        return any(item.get("name") == target for item in response.get("models", []))

    def generate(
        self,
        prompt: str,
        system_prompt: str | None,
        model: str | None,
        options: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any]]:
        started = time.monotonic()
        payload: dict[str, Any] = {
            "model": model or self.config.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if options:
            payload["options"] = options
        response = request_json(
            "POST",
            f"{self.config.ollama_url}/api/generate",
            payload,
            timeout=self.config.generation_timeout_seconds,
        )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        metrics = {
            "duration_ms": elapsed_ms,
            "model": response.get("model") or payload["model"],
            "total_duration": response.get("total_duration"),
            "load_duration": response.get("load_duration"),
            "prompt_eval_count": response.get("prompt_eval_count"),
            "eval_count": response.get("eval_count"),
            "eval_duration": response.get("eval_duration"),
        }
        return str(response.get("response") or ""), metrics
