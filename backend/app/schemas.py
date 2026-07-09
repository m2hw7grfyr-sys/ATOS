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


class SchedulerBulkApprovedCreate(BaseModel):
    post_ids: list[int] = Field(default_factory=list)
    priority: str = "MEDIUM"


class SchedulerSettingsUpdate(BaseModel):
    scheduler_enabled: bool = True
    auto_queue_on_approval: bool = False
    default_strategy: str = "ROUND_ROBIN"
    enable_random_delay: bool = False
    min_delay_seconds: int = 120
    max_delay_seconds: int = 480
    enable_platform_round_robin: bool = True
    enable_weighted_round_robin: bool = False
    max_tasks_per_account_per_day: int = 5
    max_tasks_per_platform_per_day: int = 20


class PlatformWeightUpdate(BaseModel):
    weights: list[dict[str, Any]]


class AccountCreate(BaseModel):
    platform_id: int
    username: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    account_level: Optional[str] = None
    karma_score: int = 0
    followers_count: int = 0
    following_count: int = 0
    account_age_days: int = 0
    health_score: int = 100
    risk_status: str = "LOW"
    remark: Optional[str] = None
    environment_id: Optional[str] = None
    environment_name: Optional[str] = None
    daily_limits: dict[str, Any] = Field(default_factory=dict)
    working_time: dict[str, Any] = Field(default_factory=dict)


class AccountUpdate(BaseModel):
    platform_id: Optional[int] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    account_level: Optional[str] = None
    karma_score: Optional[int] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    account_age_days: Optional[int] = None
    health_score: Optional[int] = None
    risk_status: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None
    cooling_down_until: Optional[datetime] = None
    last_failure_reason: Optional[str] = None
    failure_count_24h: Optional[int] = None
    restriction_count_7d: Optional[int] = None
    auto_downgrade_enabled: Optional[bool] = None


class TGEProfileCreate(BaseModel):
    profile_name: str
    tge_environment_id: str
    platform_id: int
    bound_account_id: Optional[int] = None
    proxy_region: Optional[str] = None
    proxy_type: Optional[str] = None
    status: str = "UNKNOWN"
    remark: Optional[str] = None


class TGEProfileUpdate(BaseModel):
    profile_name: Optional[str] = None
    tge_environment_id: Optional[str] = None
    platform_id: Optional[int] = None
    bound_account_id: Optional[int] = None
    proxy_region: Optional[str] = None
    proxy_type: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class BindTGEProfileRequest(BaseModel):
    profile_id: int


class AccountLimitUpdate(BaseModel):
    browse_daily_limit: int = 20
    like_daily_limit: int = 8
    bookmark_daily_limit: int = 5
    visit_profile_daily_limit: int = 5
    reply_daily_limit: int = 5
    dm_daily_limit: int = 0
    follow_daily_limit: int = 0
    current_browse_count: int = 0
    current_like_count: int = 0
    current_bookmark_count: int = 0
    current_visit_profile_count: int = 0
    current_reply_count: int = 0
    current_dm_count: int = 0
    current_follow_count: int = 0
    reset_at: Optional[datetime] = None


class AccountWorkingWindowsUpdate(BaseModel):
    windows: list[dict[str, Any]]


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
