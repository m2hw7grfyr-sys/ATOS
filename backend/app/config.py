from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "ATOS API"
    app_version: str = "0.15.0-production-foundation"
    app_env: str = "development"
    debug: bool = False
    database_url: str = f"sqlite:///{BACKEND_DIR / 'atos.db'}"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cookie_secure: bool = False
    default_platform: str = "reddit"
    default_ai_provider: str = "mock"
    default_ai_model: str = "mock-v0.3"
    apify_token: str = ""
    apify_api_base_url: str = "https://api.apify.com/v2"
    openai_api_key: str = ""
    log_level: str = "INFO"
    log_format: str = "json"
    log_dir: str = "storage/logs"
    log_max_bytes: int = 10_485_760
    log_backup_count: int = 7
    playwright_mock_mode: bool = True
    public_api_base_url: str = ""
    worker_api_token: str = ""
    worker_token_version: str = "v1"
    worker_heartbeat_timeout_seconds: int = 90
    admin_default_password_changed: bool = False
    production_guard_enabled: bool = True
    backup_retention_daily: int = 7
    backup_retention_weekly: int = 4
    backup_retention_monthly: int = 3
    log_retention_days: int = 14

    model_config = SettingsConfigDict(
        env_file=(
            BACKEND_DIR.parent / ".env",
            BACKEND_DIR.parent / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def normalize_database_url(self) -> "Settings":
        prefix = "sqlite:///"
        if self.database_url.startswith("sqlite:////"):
            return self
        if not self.database_url.startswith(prefix):
            return self
        raw_path = self.database_url[len(prefix) :]
        if raw_path in {":memory:", ""}:
            return self
        path = Path(raw_path)
        if not path.is_absolute():
            self.database_url = f"sqlite:///{ROOT_DIR / path}"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
