from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
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

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=new_uuid, unique=True, index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), index=True)
    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))
    source_post_id: Mapped[str] = mapped_column(String(160), index=True)
    community: Mapped[Optional[str]] = mapped_column(String(120))
    author: Mapped[Optional[str]] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(20), default="en")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)


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
