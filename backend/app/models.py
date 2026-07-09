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
    tags: Mapped[list] = mapped_column(JSON, default=list)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)


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


class AIGenerationLog(Base):
    __tablename__ = "ai_generation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id"), index=True)
    ai_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_tasks.id"), index=True)
    provider: Mapped[str] = mapped_column(String(120), index=True)
    model: Mapped[str] = mapped_column(String(160))
    prompt_version: Mapped[str] = mapped_column(String(40), default="v0.3")
    purpose: Mapped[str] = mapped_column(String(40), index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    generation_source: Mapped[str] = mapped_column(String(40), default="MOCK", index=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
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
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    risk_level: Mapped[str] = mapped_column(String(30), default="LOW", index=True)
    daily_limits: Mapped[dict] = mapped_column(JSON, default=dict)
    working_time: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class TGEProfile(Base, TimestampMixin):
    __tablename__ = "tge_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    environment_id: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(120))
    api_base_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="OFFLINE", index=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class SchedulerTask(Base, TimestampMixin):
    __tablename__ = "scheduler_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(50), index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), index=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), index=True)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id"))
    reply_id: Mapped[Optional[int]] = mapped_column(ForeignKey("replies.id"))
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)


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
