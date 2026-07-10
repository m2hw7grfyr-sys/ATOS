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


class ActorMappingCreate(BaseModel):
    data_source_id: Optional[int] = None
    actor_id: str
    platform: str
    mapping_name: str
    title_path: Optional[str] = None
    content_path: Optional[str] = None
    url_path: Optional[str] = None
    author_path: Optional[str] = None
    author_id_path: Optional[str] = None
    community_path: Optional[str] = None
    source_post_id_path: Optional[str] = None
    published_at_path: Optional[str] = None
    score_path: Optional[str] = None
    comment_count_path: Optional[str] = None
    media_path: Optional[str] = None
    language_path: Optional[str] = None
    enabled: bool = True
    remark: Optional[str] = None


class ActorMappingUpdate(BaseModel):
    data_source_id: Optional[int] = None
    actor_id: Optional[str] = None
    platform: Optional[str] = None
    mapping_name: Optional[str] = None
    title_path: Optional[str] = None
    content_path: Optional[str] = None
    url_path: Optional[str] = None
    author_path: Optional[str] = None
    author_id_path: Optional[str] = None
    community_path: Optional[str] = None
    source_post_id_path: Optional[str] = None
    published_at_path: Optional[str] = None
    score_path: Optional[str] = None
    comment_count_path: Optional[str] = None
    media_path: Optional[str] = None
    language_path: Optional[str] = None
    enabled: Optional[bool] = None
    remark: Optional[str] = None


class ActorMappingTestRequest(BaseModel):
    mapping: dict[str, Any]
    raw_item_json: dict[str, Any]


class SchedulerTaskCreate(BaseModel):
    task_type: str
    platform_id: int
    account_id: Optional[int] = None
    post_id: Optional[int] = None
    ai_task_id: Optional[int] = None
    reply_id: Optional[int] = None
    source: str = "MANUAL"
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


class TgeSettingsUpdate(BaseModel):
    tge_api_base_url: str = ""
    tge_api_key: Optional[str] = None
    default_timeout_seconds: int = 10
    enable_tge_connection_test: bool = False
    enable_auto_start_environment: bool = False
    enable_auto_attach_environment: bool = False
    enable_auto_close_tab: bool = True
    remark: Optional[str] = None


class PlaywrightSettingsUpdate(BaseModel):
    playwright_enabled: bool = False
    playwright_mock_mode: bool = True
    playwright_timeout_seconds: int = 30
    playwright_headless: bool = False
    playwright_default_wait_ms: int = 1000
    enable_screenshot: bool = True
    enable_html_snapshot: bool = True
    enable_auto_close_tab: bool = True
    enable_replay_capture: bool = True


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


class ProviderRoutingCreate(BaseModel):
    name: str
    platform: Optional[str] = None
    task_type: str = "ANALYSIS"
    strategy: Optional[str] = None
    min_commercial_score: int = 0
    max_risk_score: int = 100
    preferred_provider_id: Optional[int] = None
    fallback_provider_id: Optional[int] = None
    enabled: bool = True
    priority: int = 100
    remark: Optional[str] = None


class ProviderRoutingUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    task_type: Optional[str] = None
    strategy: Optional[str] = None
    min_commercial_score: Optional[int] = None
    max_risk_score: Optional[int] = None
    preferred_provider_id: Optional[int] = None
    fallback_provider_id: Optional[int] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    remark: Optional[str] = None


class PromptTemplateCreate(BaseModel):
    name: str
    template_type: str = "reply_prompt"
    platform: Optional[str] = None
    strategy: Optional[str] = None
    tone: Optional[str] = None
    content: str
    version: str = "v1"
    enabled: bool = True


class PromptVersionCreate(BaseModel):
    prompt_template_id: int
    version: str = "v1"
    content: str
    variables_schema: dict[str, Any] = Field(default_factory=dict)
    platform: Optional[str] = None
    strategy: Optional[str] = None
    tone: Optional[str] = None
    enabled: bool = True
    is_default: bool = False


class PromptPreviewRequest(BaseModel):
    strategy: str = "PURE_HELP"
    tone: str = "supportive"
    variables: dict[str, Any] = Field(default_factory=dict)


class PlatformSelectorCreate(BaseModel):
    platform: str
    action_type: Optional[str] = None
    selector_key: str
    selector_value: str
    selector_type: str = "css"
    version: str = "v1"
    enabled: bool = True
    remark: Optional[str] = None


class PlatformSelectorUpdate(BaseModel):
    platform: Optional[str] = None
    action_type: Optional[str] = None
    selector_key: Optional[str] = None
    selector_value: Optional[str] = None
    selector_type: Optional[str] = None
    version: Optional[str] = None
    enabled: Optional[bool] = None
    remark: Optional[str] = None


class EngagementStrategyCreate(BaseModel):
    name: str
    platform: str = "reddit"
    strategy_type: str = "MIXED_ENGAGEMENT"
    enabled: bool = True
    browse_count_min: int = 1
    browse_count_max: int = 3
    like_count_min: int = 0
    like_count_max: int = 1
    visit_profile_count_min: int = 0
    visit_profile_count_max: int = 1
    pause_min_seconds: int = 5
    pause_max_seconds: int = 30
    before_reply_enabled: bool = False
    weight: int = 10
    remark: Optional[str] = None


class EngagementStrategyUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    strategy_type: Optional[str] = None
    enabled: Optional[bool] = None
    browse_count_min: Optional[int] = None
    browse_count_max: Optional[int] = None
    like_count_min: Optional[int] = None
    like_count_max: Optional[int] = None
    visit_profile_count_min: Optional[int] = None
    visit_profile_count_max: Optional[int] = None
    pause_min_seconds: Optional[int] = None
    pause_max_seconds: Optional[int] = None
    before_reply_enabled: Optional[bool] = None
    weight: Optional[int] = None
    remark: Optional[str] = None


class EngagementTaskCreate(BaseModel):
    strategy_id: Optional[int] = None
    account_id: Optional[int] = None
    platform: str = "reddit"
    source_type: str = "POST_POOL"
    source_value: Optional[str] = None
    browse_target_count: int = 3
    like_target_count: int = 1
    visit_profile_target_count: int = 0
    priority: str = "MEDIUM"
    scheduled_at: Optional[datetime] = None


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


class PipelineRunRequest(BaseModel):
    data_source_id: Optional[int] = None
    post_ids: list[int] = Field(default_factory=list)
    auto_analyze: bool = True
    auto_approve: bool = False
    send_to_scheduler: bool = False
    priority: str = "MEDIUM"


class PipelinePostRequest(BaseModel):
    action: str = "RUN"
    auto_approve: bool = False
    send_to_scheduler: bool = False
    priority: str = "MEDIUM"


class PipelineBatchRequest(BaseModel):
    post_ids: list[int]
    action: str
    priority: str = "MEDIUM"


class AIBatchRequest(BaseModel):
    task_ids: list[int] = Field(default_factory=list)
    post_ids: list[int] = Field(default_factory=list)
    action: str
    strategy: str = "EDUCATION"
    tone: str = "supportive"


class PostBatchRequest(BaseModel):
    post_ids: list[int]
    action: str
    priority: str = "MEDIUM"


class FilterPresetCreate(BaseModel):
    name: str
    scope: str
    filters: dict[str, Any] = Field(default_factory=dict)


class SettingUpdate(BaseModel):
    value: dict[str, Any]
