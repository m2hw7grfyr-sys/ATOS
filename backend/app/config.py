from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "ATOS API"
    app_version: str = "1.0.0-rc.1"
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
    atos_studio_auth_enabled: bool = True
    atos_studio_api_token: str = ""
    studio_base_url: str = "http://127.0.0.1:8502"
    studio_push_api_token: str = ""
    studio_request_timeout_seconds: float = 10
    main_bind_host: str = "0.0.0.0"
    main_port: int = 8080
    gpu_worker_api_key: str = ""
    gpu_heartbeat_timeout_seconds: int = 30
    gpu_task_lease_seconds: int = 600
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


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "****"
    return f"{value[:8]}...{value[-4:]}"


def ensure_gpu_worker_api_key() -> str:
    settings = get_settings()
    if settings.gpu_worker_api_key:
        return settings.gpu_worker_api_key

    token = f"atos_gpu_{secrets.token_urlsafe(32)}"
    env_path = ROOT_DIR / ".env.local"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    current = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "GPU_WORKER_API_KEY=" not in current:
        prefix = "" if not current or current.endswith("\n") else "\n"
        with env_path.open("a", encoding="utf-8") as f:
            f.write(f"{prefix}GPU_WORKER_API_KEY={token}\n")
    settings.gpu_worker_api_key = token
    return token
