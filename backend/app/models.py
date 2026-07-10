from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Platform(Base, TimestampMixin):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    adapter_key: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    platform_id: Mapped[Optional[int]] = mapped_column(ForeignKey("platforms.id"))
    adapter_key: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint(
            "platform_id", "source_post_id", name="uq_posts_platform_source_post"
        ),
        UniqueConstraint("platform_id", "url_hash", name="uq_posts_platform_url_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), index=True)
    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))
    source_post_id: Mapped[Optional[str]] = mapped_column(String(160), index=True)
    url_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    community: Mapped[Optional[str]] = mapped_column(String(120))
    author: Mapped[Optional[str]] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(20), default="en")
    author_id: Mapped[Optional[str]] = mapped_column(String(160))
    score: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    media: Mapped[list] = mapped_column(JSON, default=list)
    mapping_id: Mapped[Optional[int]] = mapped_column(ForeignKey("actor_mappings.id"), index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    pipeline_stage: Mapped[str] = mapped_column(String(40), default="NEW", index=True)
    ready_for_ai_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ai_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)


class PostTimeline(Base):
    __tablename__ = "post_timelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    event_name: Mapped[str] = mapped_column(String(120), index=True)
    old_status: Mapped[Optional[str]] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class BusinessEvent(Base):
    __tablename__ = "business_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    event_name: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="PUBLISHED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id"), index=True
    )
    platform: Mapped[str] = mapped_column(String(80), index=True)
    actor_id: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(30), default="RUNNING", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    raw_response_excerpt: Mapped[Optional[str]] = mapped_column(Text)
    mapping_id: Mapped[Optional[int]] = mapped_column(ForeignKey("actor_mappings.id"), index=True)
    mapping_missing: Mapped[bool] = mapped_column(Boolean, default=False)
    incomplete_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_failed_count: Mapped[int] = mapped_column(Integer, default=0)
    normalization_warning_count: Mapped[int] = mapped_column(Integer, default=0)


class ActorMapping(Base, TimestampMixin):
    __tablename__ = "actor_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(200), index=True)
    platform: Mapped[str] = mapped_column(String(80), index=True)
    mapping_name: Mapped[str] = mapped_column(String(160))
    title_path: Mapped[Optional[str]] = mapped_column(String(300))
    content_path: Mapped[Optional[str]] = mapped_column(String(300))
    url_path: Mapped[Optional[str]] = mapped_column(String(300))
    author_path: Mapped[Optional[str]] = mapped_column(String(300))
    author_id_path: Mapped[Optional[str]] = mapped_column(String(300))
    community_path: Mapped[Optional[str]] = mapped_column(String(300))
    source_post_id_path: Mapped[Optional[str]] = mapped_column(String(300))
    published_at_path: Mapped[Optional[str]] = mapped_column(String(300))
    score_path: Mapped[Optional[str]] = mapped_column(String(300))
    comment_count_path: Mapped[Optional[str]] = mapped_column(String(300))
    media_path: Mapped[Optional[str]] = mapped_column(String(300))
    language_path: Mapped[Optional[str]] = mapped_column(String(300))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class AITask(Base, TimestampMixin):
    __tablename__ = "ai_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    strategy: Mapped[str] = mapped_column(String(80), default="EDUCATION")
    commercial_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    provider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_providers.id"), index=True)
    fallback_provider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_providers.id"), index=True)
    prompt_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prompt_versions.id"), index=True)
    generation_source: Mapped[str] = mapped_column(String(40), default="MOCK", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)


class LLMProvider(Base, TimestampMixin):
    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(40), index=True)
    api_base_url: Mapped[Optional[str]] = mapped_column(String(500))
    api_key: Mapped[Optional[str]] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(160), default="mock-v0.3")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    use_for_analysis: Mapped[bool] = mapped_column(Boolean, default=True)
    use_for_reply: Mapped[bool] = mapped_column(Boolean, default=True)
    use_for_embedding: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    max_retries: Mapped[int] = mapped_column(Integer, default=1)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    health_status: Mapped[str] = mapped_column(String(30), default="UNKNOWN", index=True)
    last_health_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_health_error: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class ProviderRouting(Base, TimestampMixin):
    __tablename__ = "provider_routing"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    platform: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    task_type: Mapped[str] = mapped_column(String(40), index=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    min_commercial_score: Mapped[int] = mapped_column(Integer, default=0)
    max_risk_score: Mapped[int] = mapped_column(Integer, default=100)
    preferred_provider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_providers.id"), index=True)
    fallback_provider_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_providers.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class AIAnalysisResult(Base, TimestampMixin):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    ai_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_tasks.id"), index=True)
    intent: Mapped[Optional[str]] = mapped_column(String(120))
    pain_point: Mapped[Optional[str]] = mapped_column(Text)
    commercial_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    recommended_strategy: Mapped[Optional[str]] = mapped_column(String(120))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    provider_used: Mapped[str] = mapped_column(String(120), default="mock")
    model_used: Mapped[str] = mapped_column(String(160), default="mock-v0.3")
    generation_source: Mapped[str] = mapped_column(String(40), default="MOCK", index=True)
    raw_result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class Reply(Base, TimestampMixin):
    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    ai_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_tasks.id"))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default="LLM_GENERATED")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="GENERATED", index=True)


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    template_type: Mapped[str] = mapped_column(String(40), index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    tone: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40), default="v0.3")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class PromptVersion(Base, TimestampMixin):
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    prompt_template_id: Mapped[int] = mapped_column(ForeignKey("prompt_templates.id"), index=True)
    version: Mapped[str] = mapped_column(String(40), default="v1")
    content: Mapped[str] = mapped_column(Text)
    variables_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    platform: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    tone: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class AIGenerationLog(Base):
    __tablename__ = "ai_generation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id"), index=True)
    ai_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_tasks.id"), index=True)
    provider: Mapped[str] = mapped_column(String(120), index=True)
    model: Mapped[str] = mapped_column(String(160))
    prompt_version: Mapped[str] = mapped_column(String(40), default="v0.3")
    prompt_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prompt_versions.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(40), index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    provider_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    generation_source: Mapped[str] = mapped_column(String(40), default="MOCK", index=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text)
    fallback_from_provider: Mapped[Optional[str]] = mapped_column(String(120))
    fallback_to_provider: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="SUCCESS", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), index=True)
    username: Mapped[str] = mapped_column(String(120))
    display_name: Mapped[Optional[str]] = mapped_column(String(160))
    profile_url: Mapped[Optional[str]] = mapped_column(String(1000))
    account_level: Mapped[Optional[str]] = mapped_column(String(60))
    karma_score: Mapped[int] = mapped_column(Integer, default=0)
    followers_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    account_age_days: Mapped[int] = mapped_column(Integer, default=0)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    risk_level: Mapped[str] = mapped_column(String(30), default="LOW", index=True)
    risk_status: Mapped[str] = mapped_column(String(30), default="LOW", index=True)
    daily_limits: Mapped[dict] = mapped_column(JSON, default=dict)
    working_time: Mapped[dict] = mapped_column(JSON, default=dict)
    cooling_down_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_failure_reason: Mapped[Optional[str]] = mapped_column(Text)
    failure_count_24h: Mapped[int] = mapped_column(Integer, default=0)
    restriction_count_7d: Mapped[int] = mapped_column(Integer, default=0)
    auto_downgrade_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class TGEProfile(Base, TimestampMixin):
    __tablename__ = "tge_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), unique=True)
    bound_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), unique=True, index=True)
    platform_id: Mapped[Optional[int]] = mapped_column(ForeignKey("platforms.id"), index=True)
    environment_id: Mapped[Optional[str]] = mapped_column(String(120))
    tge_environment_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(120))
    profile_name: Mapped[Optional[str]] = mapped_column(String(120))
    api_base_url: Mapped[Optional[str]] = mapped_column(String(500))
    proxy_region: Mapped[Optional[str]] = mapped_column(String(80))
    proxy_type: Mapped[Optional[str]] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="UNKNOWN", index=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    remark: Mapped[Optional[str]] = mapped_column(Text)
    connection_status: Mapped[str] = mapped_column(String(40), default="UNKNOWN", index=True)
    last_connection_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_connection_error: Mapped[Optional[str]] = mapped_column(Text)
    runtime_status: Mapped[str] = mapped_column(String(40), default="UNKNOWN", index=True)
    websocket_url: Mapped[Optional[str]] = mapped_column(String(1000))
    debug_port: Mapped[Optional[int]] = mapped_column(Integer)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AccountLimit(Base, TimestampMixin):
    __tablename__ = "account_limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True, index=True)
    browse_daily_limit: Mapped[int] = mapped_column(Integer, default=20)
    like_daily_limit: Mapped[int] = mapped_column(Integer, default=8)
    bookmark_daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    visit_profile_daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    reply_daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    dm_daily_limit: Mapped[int] = mapped_column(Integer, default=0)
    follow_daily_limit: Mapped[int] = mapped_column(Integer, default=0)
    current_browse_count: Mapped[int] = mapped_column(Integer, default=0)
    current_like_count: Mapped[int] = mapped_column(Integer, default=0)
    current_bookmark_count: Mapped[int] = mapped_column(Integer, default=0)
    current_visit_profile_count: Mapped[int] = mapped_column(Integer, default=0)
    current_reply_count: Mapped[int] = mapped_column(Integer, default=0)
    current_dm_count: Mapped[int] = mapped_column(Integer, default=0)
    current_follow_count: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AccountWorkingWindow(Base, TimestampMixin):
    __tablename__ = "account_working_windows"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    day_of_week: Mapped[str] = mapped_column(String(10), index=True)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Shanghai")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class SchedulerTask(Base, TimestampMixin):
    __tablename__ = "scheduler_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(50), index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), index=True)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id"))
    ai_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_tasks.id"), index=True)
    reply_id: Mapped[Optional[int]] = mapped_column(ForeignKey("replies.id"))
    source: Mapped[str] = mapped_column(String(60), default="MANUAL", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    earliest_execute_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)


class SchedulerLog(Base):
    __tablename__ = "scheduler_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("scheduler_tasks.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    old_status: Mapped[Optional[str]] = mapped_column(String(30))
    new_status: Mapped[Optional[str]] = mapped_column(String(30))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    selected_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), index=True)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class PlatformWeight(Base, TimestampMixin):
    __tablename__ = "platform_weights"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), unique=True, index=True)
    weight: Mapped[int] = mapped_column(Integer, default=10)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class ExecutionTask(Base, TimestampMixin):
    __tablename__ = "execution_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    scheduler_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scheduler_tasks.id"), unique=True, index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), index=True)
    tge_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tge_profiles.id"), index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    action_type: Mapped[str] = mapped_column(String(60), default="OPEN_PAGE", index=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(120))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="NEW", index=True)
    queue_status: Mapped[str] = mapped_column(String(40), default="NEW", index=True)
    worker_node_id: Mapped[Optional[int]] = mapped_column(ForeignKey("worker_nodes.id"), index=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    precheck_status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    environment_status: Mapped[str] = mapped_column(String(40), default="UNKNOWN", index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    execution_task_id: Mapped[int] = mapped_column(ForeignKey("execution_tasks.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    old_status: Mapped[Optional[str]] = mapped_column(String(40))
    new_status: Mapped[Optional[str]] = mapped_column(String(40))
    message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class WorkerNode(Base, TimestampMixin):
    __tablename__ = "worker_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="ONLINE", index=True)
    host: Mapped[Optional[str]] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(60), default="local")
    capability: Mapped[dict] = mapped_column(JSON, default=dict)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)


class ExecutionQueue(Base):
    __tablename__ = "execution_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    scheduler_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scheduler_tasks.id"), index=True)
    execution_task_id: Mapped[int] = mapped_column(ForeignKey("execution_tasks.id"), unique=True, index=True)
    worker_node_id: Mapped[Optional[int]] = mapped_column(ForeignKey("worker_nodes.id"), index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(40), default="QUEUED", index=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class BrowserSession(Base, TimestampMixin):
    __tablename__ = "browser_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    browser_type: Mapped[str] = mapped_column(String(60), default="mock", index=True)
    worker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("worker_nodes.id"), index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), index=True)
    profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tge_profiles.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="RUNNING", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class BrowserTab(Base):
    __tablename__ = "browser_tabs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("browser_sessions.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), default="OPEN", index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class PlatformSelector(Base, TimestampMixin):
    __tablename__ = "platform_selectors"
    __table_args__ = (
        UniqueConstraint(
            "platform", "selector_key", "selector_value", name="uq_platform_selector_value"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(80), index=True)
    selector_key: Mapped[str] = mapped_column(String(120), index=True)
    selector_value: Mapped[str] = mapped_column(String(1000))
    selector_type: Mapped[str] = mapped_column(String(40), default="css")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class EngagementStrategy(Base, TimestampMixin):
    __tablename__ = "engagement_strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    platform: Mapped[str] = mapped_column(String(80), index=True)
    strategy_type: Mapped[str] = mapped_column(String(80), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    browse_count_min: Mapped[int] = mapped_column(Integer, default=0)
    browse_count_max: Mapped[int] = mapped_column(Integer, default=0)
    like_count_min: Mapped[int] = mapped_column(Integer, default=0)
    like_count_max: Mapped[int] = mapped_column(Integer, default=0)
    visit_profile_count_min: Mapped[int] = mapped_column(Integer, default=0)
    visit_profile_count_max: Mapped[int] = mapped_column(Integer, default=0)
    pause_min_seconds: Mapped[int] = mapped_column(Integer, default=5)
    pause_max_seconds: Mapped[int] = mapped_column(Integer, default=30)
    before_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, default=10)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class EngagementTask(Base, TimestampMixin):
    __tablename__ = "engagement_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    strategy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("engagement_strategies.id"), index=True)
    scheduler_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scheduler_tasks.id"), index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), index=True)
    platform: Mapped[str] = mapped_column(String(80), index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="POST_POOL", index=True)
    source_value: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="NEW", index=True)
    browse_target_count: Mapped[int] = mapped_column(Integer, default=0)
    like_target_count: Mapped[int] = mapped_column(Integer, default=0)
    visit_profile_target_count: Mapped[int] = mapped_column(Integer, default=0)
    browse_done_count: Mapped[int] = mapped_column(Integer, default=0)
    like_done_count: Mapped[int] = mapped_column(Integer, default=0)
    visit_profile_done_count: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class ReplayFile(Base):
    __tablename__ = "replay_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    execution_task_id: Mapped[int] = mapped_column(ForeignKey("execution_tasks.id"), index=True)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(1000))
    before_fill_screenshot_path: Mapped[Optional[str]] = mapped_column(String(1000))
    after_fill_screenshot_path: Mapped[Optional[str]] = mapped_column(String(1000))
    html_path: Mapped[Optional[str]] = mapped_column(String(1000))
    console_log_path: Mapped[Optional[str]] = mapped_column(String(1000))
    network_log_path: Mapped[Optional[str]] = mapped_column(String(1000))
    timeline_path: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReplayIndex(Base):
    __tablename__ = "replay_indexes"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    execution_task_id: Mapped[int] = mapped_column(ForeignKey("execution_tasks.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="INDEXED", index=True)
    artifact_count: Mapped[int] = mapped_column(Integer, default=0)
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    category: Mapped[str] = mapped_column(String(60), index=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class StatisticSnapshot(Base, TimestampMixin):
    __tablename__ = "statistics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    metric: Mapped[str] = mapped_column(String(120), index=True)
    dimension: Mapped[str] = mapped_column(String(80), default="SYSTEM", index=True)
    value: Mapped[float] = mapped_column(Float, default=0)
    period: Mapped[str] = mapped_column(String(30), default="TODAY", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(80))
    entity_uuid: Mapped[Optional[str]] = mapped_column(String(36))
    actor: Mapped[str] = mapped_column(String(120), default="system")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FilterPreset(Base, TimestampMixin):
    __tablename__ = "filter_presets"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    scope: Mapped[str] = mapped_column(String(60), index=True)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
