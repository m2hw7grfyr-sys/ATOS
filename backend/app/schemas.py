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
    apify_token: Optional[str] = None
    enabled: bool = True


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    platform_id: Optional[int] = None
    config: Optional[dict[str, Any]] = None
    apify_token: Optional[str] = None
    enabled: Optional[bool] = None


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
    environment_id: Optional[str] = None
    environment_name: Optional[str] = None
    daily_limits: dict[str, Any] = Field(default_factory=dict)
    working_time: dict[str, Any] = Field(default_factory=dict)


class MockAIGenerateRequest(BaseModel):
    post_id: int
    strategy: str = "EDUCATION"


class ReplyGenerateRequest(BaseModel):
    strategy: str = "EDUCATION"
    tone: str = "supportive"
    variables: dict[str, Any] = Field(default_factory=dict)


class ReplyUpdate(BaseModel):
    content: str


class LLMProviderCreate(BaseModel):
    provider_name: str
    provider_type: str = "mock"
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: str = "mock-v0.3"
    enabled: bool = True
    priority: int = 100
    use_for_analysis: bool = True
    use_for_reply: bool = True
    use_for_embedding: bool = False
    is_mock: bool = False
    timeout_seconds: int = 30
    max_retries: int = 1
    remark: Optional[str] = None


class LLMProviderUpdate(BaseModel):
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    use_for_analysis: Optional[bool] = None
    use_for_reply: Optional[bool] = None
    use_for_embedding: Optional[bool] = None
    is_mock: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    remark: Optional[str] = None


class SchedulerApprovedTaskCreate(BaseModel):
    ai_task_id: int
    account_id: Optional[int] = None
    priority: str = "MEDIUM"


class SettingUpdate(BaseModel):
    value: dict[str, Any]
