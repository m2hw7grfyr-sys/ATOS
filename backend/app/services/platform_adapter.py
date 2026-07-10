from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.base import PlatformAdapter
from app.adapters.reddit import RedditAdapter
from app.services.platform_runtime import PlatformRuntime


def adapter_for_platform(platform: str, db: Session, mock_mode: bool = True) -> PlatformAdapter:
    return PlatformRuntime(db, mock_mode=mock_mode).adapter_for(platform)


__all__ = ["PlatformAdapter", "RedditAdapter", "adapter_for_platform"]
