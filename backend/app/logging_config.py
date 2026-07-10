from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": getattr(record, "atos_module", record.name),
            "action": getattr(record, "action", None),
            "trace_id": getattr(record, "trace_id", None),
            "request_id": getattr(record, "request_id", None),
            "duration": getattr(record, "duration", None),
            "result": getattr(record, "result", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if settings.log_format == "json" else logging.Formatter("%(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
