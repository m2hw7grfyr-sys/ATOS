from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountLimit,
    EngagementStrategy,
    EngagementTask,
    Platform,
    SchedulerTask,
    StatisticSnapshot,
)
from app.services.scheduler import set_status


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def platform_for_slug(db: Session, slug: str) -> Platform | None:
    return db.scalar(select(Platform).where(Platform.slug == slug))


def create_engagement_task(db: Session, values: dict[str, Any]) -> EngagementTask:
    strategy = db.get(EngagementStrategy, values.get("strategy_id")) if values.get("strategy_id") else None
    if strategy:
        values = {
            **values,
            "platform": values.get("platform") or strategy.platform,
            "browse_target_count": values.get("browse_target_count") or random.randint(strategy.browse_count_min, max(strategy.browse_count_min, strategy.browse_count_max)),
            "like_target_count": values.get("like_target_count") or random.randint(strategy.like_count_min, max(strategy.like_count_min, strategy.like_count_max)),
            "visit_profile_target_count": values.get("visit_profile_target_count") or random.randint(strategy.visit_profile_count_min, max(strategy.visit_profile_count_min, strategy.visit_profile_count_max)),
        }
    task = EngagementTask(**values, status="NEW")
    db.add(task)
    db.flush()
    return task


def queue_engagement_task(db: Session, task: EngagementTask) -> SchedulerTask:
    platform = platform_for_slug(db, task.platform)
    if not platform:
        raise ValueError("platform not found")
    existing = db.scalar(
        select(SchedulerTask).where(
            SchedulerTask.task_type == "ENGAGEMENT",
            SchedulerTask.payload["engagement_task_id"].as_integer() == task.id,
            SchedulerTask.status.in_(["NEW", "QUEUED", "DELAYED", "READY", "DISPATCHED"]),
        )
    )
    if existing:
        return existing
    scheduler_task = SchedulerTask(
        task_type="ENGAGEMENT",
        platform_id=platform.id,
        account_id=task.account_id,
        priority=task.priority,
        scheduled_at=task.scheduled_at,
        payload={
            "engagement_task_id": task.id,
            "strategy_id": task.strategy_id,
            "strategy_type": db.get(EngagementStrategy, task.strategy_id).strategy_type if task.strategy_id else "CUSTOM",
            "action_type": "MIXED_ENGAGEMENT",
            "source_type": task.source_type,
            "source_value": task.source_value,
            "browse_target_count": task.browse_target_count,
            "like_target_count": task.like_target_count,
            "visit_profile_target_count": task.visit_profile_target_count,
        },
        status="NEW",
    )
    db.add(scheduler_task)
    db.flush()
    task.scheduler_task_id = scheduler_task.id
    task.status = "QUEUED"
    set_status(db, scheduler_task, "QUEUED", action="QUEUE_ENGAGEMENT", reason="Engagement task queued")
    return scheduler_task


def execute_engagement_mock(db: Session, task: EngagementTask) -> EngagementTask:
    task.status = "RUNNING"
    task.started_at = task.started_at or utc_now()
    task.browse_done_count = task.browse_target_count
    task.like_done_count = task.like_target_count
    task.visit_profile_done_count = task.visit_profile_target_count
    task.status = "SUCCESS"
    task.finished_at = utc_now()
    if task.account_id:
        account = db.get(Account, task.account_id)
        if account:
            account.last_active_at = utc_now()
            account.health_score = min(100, (account.health_score or 0) + 1)
        limits = db.scalar(select(AccountLimit).where(AccountLimit.account_id == task.account_id))
        if limits:
            limits.current_browse_count += task.browse_done_count
            limits.current_like_count += task.like_done_count
            limits.current_visit_profile_count += task.visit_profile_done_count
    for metric, value in [
        ("browse_count", task.browse_done_count),
        ("like_count", task.like_done_count),
        ("visit_profile_count", task.visit_profile_done_count),
        ("engagement_success_rate", 100),
    ]:
        stat = db.scalar(
            select(StatisticSnapshot).where(
                StatisticSnapshot.metric == metric,
                StatisticSnapshot.dimension == task.platform.upper(),
                StatisticSnapshot.period == "TODAY",
            )
        )
        if stat:
            stat.value = float(stat.value or 0) + float(value)
        else:
            db.add(
                StatisticSnapshot(
                    metric=metric,
                    dimension=task.platform.upper(),
                    value=float(value),
                    period="TODAY",
                    metadata_json={"source": "engagement_mock"},
                )
            )
    return task


def create_reply_warmup_tasks(db: Session, scheduler_task: SchedulerTask) -> list[EngagementTask]:
    platform = db.get(Platform, scheduler_task.platform_id)
    if not platform:
        return []
    strategies = db.scalars(
        select(EngagementStrategy).where(
            EngagementStrategy.platform == platform.slug,
            EngagementStrategy.enabled.is_(True),
            EngagementStrategy.before_reply_enabled.is_(True),
        )
    ).all()
    created = []
    for strategy in strategies:
        task = create_engagement_task(
            db,
            {
                "strategy_id": strategy.id,
                "account_id": scheduler_task.account_id,
                "platform": platform.slug,
                "source_type": "POST_POOL",
                "source_value": str(scheduler_task.post_id or ""),
                "browse_target_count": random.randint(strategy.browse_count_min, max(strategy.browse_count_min, strategy.browse_count_max)),
                "like_target_count": random.randint(strategy.like_count_min, max(strategy.like_count_min, strategy.like_count_max)),
                "visit_profile_target_count": random.randint(strategy.visit_profile_count_min, max(strategy.visit_profile_count_min, strategy.visit_profile_count_max)),
                "priority": scheduler_task.priority,
            },
        )
        queue_engagement_task(db, task)
        created.append(task)
    return created
