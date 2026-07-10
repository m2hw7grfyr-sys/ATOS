from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import SystemSetting


class ConfigurationService:
    """Single read path for runtime configuration.

    Environment variables provide boot-time defaults. Persistent overrides live
    in `system_settings` and should be accessed through this service.
    """

    def __init__(self, db: Session | None = None):
        self.db = db
        self.env = get_settings()

    def get(self, key: str, default: Any = None) -> Any:
        if self.db:
            item = self.db.scalar(select(SystemSetting).where(SystemSetting.key == key))
            if item:
                return item.value
        return getattr(self.env, key, default)

    def get_public_settings(self) -> dict[str, Any]:
        return {
            "app_name": self.env.app_name,
            "app_version": self.env.app_version,
            "app_env": self.env.app_env,
            "api_base_url": getattr(self.env, "api_base_url", ""),
            "default_platform": self.env.default_platform,
            "default_ai_provider": self.env.default_ai_provider,
            "playwright_mock_mode": self.env.playwright_mock_mode,
        }
