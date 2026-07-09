from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "ATOS API"
    app_version: str = "1.1.0"
    app_env: str = "development"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'atos.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    default_platform: str = "reddit"
    default_ai_provider: str = "mock"
    default_ai_model: str = "mock-v0.3"
    apify_token: str = ""
    apify_api_base_url: str = "https://api.apify.com/v2"
    openai_api_key: str = ""
    playwright_mock_mode: bool = True

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
