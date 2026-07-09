from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    name: str
    source_type: str = "APIFY"
    platform_id: Optional[int] = None
    adapter_key: str = "apify"
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SchedulerTaskCreate(BaseModel):
    task_type: str
    platform_id: int
    account_id: Optional[int] = None
    post_id: Optional[int] = None
    reply_id: Optional[int] = None
    priority: str = "MEDIUM"
    scheduled_at: Optional[datetime] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AccountCreate(BaseModel):
    platform_id: int
    username: str
    display_name: Optional[str] = None
    daily_limits: dict[str, Any] = Field(default_factory=dict)
    working_time: dict[str, Any] = Field(default_factory=dict)


class SettingUpdate(BaseModel):
    value: dict[str, Any]
