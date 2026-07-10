from __future__ import annotations

import random
from datetime import datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AITask,
    Account,
    AccountLimit,
    AccountWorkingWindow,
    Platform,
    PlatformWeight,
    Post,
    Reply,
    ReplyTask,
    SchedulerLog,
    SchedulerTask,
    SystemSetting,
    TGEProfile,
)
from app.services.execution import ExecutionRuntime


DEFAULT_SCHEDULER_SETTINGS = {
    "scheduler_enabled": True,
    "auto_queue_on_approval": False,
    "default_strategy": "ROUND_ROBIN",
    "enable_random_delay": False,
    "min_delay_seconds": 120,
    "max_delay_seconds": 480,
    "enable_platform_round_robin": True,
    "enable_weighted_round_robin": False,
    "max_tasks_per_account_per_day": 5,
    "max_tasks_per_platform_per_day": 20,
    "last_dispatched_platform_id": None,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_scheduler_settings(db: Session) -> dict[str, Any]:
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "scheduler.defaults"))
    values = dict(DEFAULT_SCHEDULER_SETTINGS)
    if setting and setting.value:
        values.update(setting.value)
    return values


def save_scheduler_settings(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_SCHEDULER_SETTINGS)
    merged.update(values)
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "scheduler.defaults"))
    if setting:
        setting.value = merged
    else:
        db.add(SystemSetting(key="scheduler.defaults", category="SCHEDULER", value=merged))
    db.commit()
    return merged


def log_task(
    db: Session,
    task: SchedulerTask,
    *,
    action: str,
    old_status: str | None,
    new_status: str | None,
    reason: str | None = None,
    selected_account_id: int | None = None,
    delay_seconds: int = 0,
) -> None:
    db.add(
        SchedulerLog(
            task_id=task.id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            selected_account_id=selected_account_id,
            delay_seconds=delay_seconds,
        )
    )


def set_status(
    db: Session,
    task: SchedulerTask,
    new_status: str,
    *,
    action: str,
    reason: str | None = None,
    selected_account_id: int | None = None,
    delay_seconds: int = 0,
) -> None:
    old_status = task.status
    task.status = new_status
    log_task(
        db,
        task,
        action=action,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        selected_account_id=selected_account_id,
        delay_seconds=delay_seconds,
    )


def queue_approved_ai_task(
    db: Session,
    *,
    ai_task_id: int,
    account_id: int | None = None,
    priority: str = "MEDIUM",
    source: str = "AI_WORKSPACE",
) -> SchedulerTask:
    ai_task = db.get(AITask, ai_task_id)
    if not ai_task or ai_task.status != "APPROVED":
        raise ValueError("AI task must be approved")
    reply = db.scalar(
        select(Reply)
        .where(Reply.ai_task_id == ai_task.id, Reply.status == "APPROVED")
        .order_by(Reply.version.desc(), Reply.id.desc())
    )
    post = db.get(Post, ai_task.post_id)
    if not reply or not post:
        raise ValueError("approved reply or post missing")
    existing = db.scalar(
        select(SchedulerTask).where(
            SchedulerTask.reply_id == reply.id,
            SchedulerTask.status.in_(["NEW", "QUEUED", "DELAYED", "READY", "DISPATCHED"]),
        )
    )
    if existing:
        existing.ai_task_id = existing.ai_task_id or ai_task.id
        existing.source = existing.source or source
        return existing
    platform = db.get(Platform, post.platform_id) if post.platform_id else None
    reply_task = db.scalar(
        select(ReplyTask).where(
            ReplyTask.reply_id == reply.id,
            ReplyTask.status.in_(["CREATED", "APPROVED", "SCHEDULED", "EXECUTING", "WAITING_MANUAL"]),
        )
    )
    if not reply_task:
        reply_task = ReplyTask(
            post_id=post.id,
            reply_id=reply.id,
            platform=platform.slug if platform else None,
            account_id=account_id,
            reply_content=reply.content,
            execution_mode="SEMI_AUTO",
            status="APPROVED",
        )
        db.add(reply_task)
        db.flush()
    task = SchedulerTask(
        task_type="REPLY_TASK",
        platform_id=post.platform_id,
        account_id=account_id,
        post_id=post.id,
        ai_task_id=ai_task.id,
        reply_id=reply.id,
        reply_task_id=reply_task.id,
        source=source,
        priority=priority.upper(),
        payload={
            "task_type": "PREPARE_REPLY",
            "ai_task_id": ai_task.id,
            "reply_task_id": reply_task.id,
            "strategy": ai_task.strategy,
            "mode": "SEMI_AUTO",
            "action_type": "PREPARE_REPLY",
            "url": post.url,
            "post_url": post.url,
            "reply_content": reply.content,
            "execution_mode": "SEMI_AUTO",
            "metadata": {"reply_id": reply.id, "reply_task_id": reply_task.id},
        },
        status="NEW",
    )
    db.add(task)
    db.flush()
    set_status(db, task, "QUEUED", action="QUEUE_APPROVED", reason="Approved AI reply queued")
    reply_task.scheduler_task_id = task.id
    reply_task.status = "SCHEDULED"
    return task


def parse_windows(account: Account) -> list[dict[str, str]]:
    value = account.working_time or {}
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("windows"), list):
            return value["windows"]
        if isinstance(value.get("ranges"), list):
            day = utc_now().strftime("%a").upper()[:3]
            return [
                {"day": day, "start": item.split("-")[0], "end": item.split("-")[-1]}
                for item in value["ranges"]
                if isinstance(item, str) and "-" in item
            ]
    return []


def account_in_working_time(db: Session, account: Account, now: datetime | None = None) -> bool:
    now = now or utc_now()
    db_windows = db.scalars(
        select(AccountWorkingWindow).where(
            AccountWorkingWindow.account_id == account.id,
            AccountWorkingWindow.enabled.is_(True),
        )
    ).all()
    windows = [
        {"day": item.day_of_week, "start": item.start_time, "end": item.end_time}
        for item in db_windows
    ] or parse_windows(account)
    if not windows:
        return True
    today = now.strftime("%a").upper()[:3]
    current = now.time()
    for window in windows:
        if str(window.get("day", "")).upper() != today:
            continue
        try:
            start_hour, start_minute = [int(part) for part in str(window["start"]).split(":")[:2]]
            end_hour, end_minute = [int(part) for part in str(window["end"]).split(":")[:2]]
        except (KeyError, ValueError):
            continue
        if time(start_hour, start_minute) <= current <= time(end_hour, end_minute):
            return True
    return False


def account_daily_count(db: Session, account_id: int, task_type: str) -> int:
    start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.count())
        .select_from(SchedulerTask)
        .where(
            SchedulerTask.account_id == account_id,
            SchedulerTask.task_type == task_type,
            SchedulerTask.created_at >= start,
            SchedulerTask.status.in_(["READY", "DISPATCHED"]),
        )
    ) or 0


def account_limit_available(db: Session, account: Account, task_type: str, settings: dict[str, Any]) -> tuple[bool, str | None]:
    limits = db.scalar(select(AccountLimit).where(AccountLimit.account_id == account.id))
    if limits and task_type in {"REPLY", "REPLY_TASK"}:
        if limits.current_reply_count >= limits.reply_daily_limit:
            return False, "Daily reply limit reached"
        return True, None
    legacy_limits = account.daily_limits or {}
    reply_limit = int(legacy_limits.get("reply", settings.get("max_tasks_per_account_per_day", 5)))
    if task_type in {"REPLY", "REPLY_TASK"} and account_daily_count(db, account.id, task_type) >= reply_limit:
        return False, "Daily reply limit reached"
    return True, None


def account_has_tge_profile(db: Session, account: Account) -> bool:
    profile = db.scalar(
        select(TGEProfile).where(
            (TGEProfile.bound_account_id == account.id) | (TGEProfile.account_id == account.id)
        )
    )
    return profile is not None


def select_account_for_task(
    db: Session, task: SchedulerTask, settings: dict[str, Any]
) -> tuple[Account | None, str | None]:
    now = utc_now()
    candidates = db.scalars(
        select(Account)
        .where(Account.platform_id == task.platform_id, Account.status == "ACTIVE")
        .order_by(Account.health_score.desc(), Account.id.asc())
    ).all()
    if not candidates:
        return None, "No available account"
    for account in candidates:
        risk_status = account.risk_status or account.risk_level
        if risk_status in {"HIGH", "CRITICAL"}:
            log_task(db, task, action="ACCOUNT_REJECTED", old_status=task.status, new_status=task.status, reason="Risk status blocked", selected_account_id=account.id)
            continue
        if account.cooling_down_until and account.cooling_down_until > now:
            log_task(db, task, action="ACCOUNT_REJECTED", old_status=task.status, new_status=task.status, reason="Account cooling down", selected_account_id=account.id)
            continue
        if not account_in_working_time(db, account, now):
            log_task(db, task, action="ACCOUNT_REJECTED", old_status=task.status, new_status=task.status, reason="Outside working time", selected_account_id=account.id)
            continue
        limit_ok, limit_reason = account_limit_available(db, account, task.task_type, settings)
        if not limit_ok:
            log_task(db, task, action="ACCOUNT_REJECTED", old_status=task.status, new_status=task.status, reason=limit_reason, selected_account_id=account.id)
            continue
        if not account_has_tge_profile(db, account):
            log_task(db, task, action="ACCOUNT_REJECTED", old_status=task.status, new_status=task.status, reason="No TGE profile binding", selected_account_id=account.id)
            continue
        return account, None
    return None, "No available account"


def weighted_platform_order(db: Session, platform_ids: list[int]) -> list[int]:
    weights = {
        item.platform_id: max(1, item.weight)
        for item in db.scalars(
            select(PlatformWeight).where(PlatformWeight.enabled.is_(True))
        ).all()
    }
    ordered = sorted(platform_ids, key=lambda pid: (-weights.get(pid, 1), pid))
    result: list[int] = []
    remaining = {pid: weights.get(pid, 1) for pid in ordered}
    while remaining:
        for pid in list(ordered):
            if remaining.get(pid, 0) <= 0:
                remaining.pop(pid, None)
                continue
            result.append(pid)
            remaining[pid] -= 1
    return result


def choose_next_task(db: Session, tasks: list[SchedulerTask], settings: dict[str, Any]) -> SchedulerTask | None:
    if not tasks:
        return None
    by_platform: dict[int, list[SchedulerTask]] = {}
    for task in tasks:
        by_platform.setdefault(task.platform_id, []).append(task)
    platform_ids = list(by_platform)
    last_platform_id = settings.get("last_dispatched_platform_id")
    if settings.get("enable_weighted_round_robin"):
        order = weighted_platform_order(db, platform_ids)
    elif settings.get("enable_platform_round_robin", True):
        order = sorted(platform_ids)
    else:
        return tasks[0]
    if len(order) > 1 and last_platform_id in order:
        order = [pid for pid in order if pid != last_platform_id] + [last_platform_id]
    for platform_id in order:
        candidates = by_platform.get(platform_id)
        if candidates:
            return candidates[0]
    return tasks[0]


def apply_delay_if_needed(db: Session, task: SchedulerTask, settings: dict[str, Any]) -> bool:
    if not settings.get("enable_random_delay"):
        return False
    if task.delay_seconds and task.earliest_execute_at:
        return False
    min_delay = int(settings.get("min_delay_seconds", 120))
    max_delay = int(settings.get("max_delay_seconds", 480))
    if max_delay < min_delay:
        max_delay = min_delay
    delay_seconds = random.randint(min_delay, max_delay)
    task.delay_seconds = delay_seconds
    task.earliest_execute_at = utc_now() + timedelta(seconds=delay_seconds)
    set_status(db, task, "DELAYED", action="APPLY_DELAY", reason="Random delay applied", delay_seconds=delay_seconds)
    return True


def run_once(db: Session) -> dict[str, Any]:
    settings = get_scheduler_settings(db)
    if not settings.get("scheduler_enabled", True):
        return {"status": "PAUSED", "processed": 0}
    now = utc_now()
    delayed = db.scalars(
        select(SchedulerTask).where(
            SchedulerTask.status == "DELAYED",
            SchedulerTask.earliest_execute_at.is_not(None),
            SchedulerTask.earliest_execute_at <= now,
        )
    ).all()
    for task in delayed:
        set_status(db, task, "QUEUED", action="DELAY_DONE", reason="Earliest execute time reached")

    queue = db.scalars(
        select(SchedulerTask)
        .where(SchedulerTask.status.in_(["NEW", "QUEUED"]))
        .order_by(SchedulerTask.priority.asc(), SchedulerTask.created_at.asc())
    ).all()
    selected = choose_next_task(db, queue, settings)
    if not selected:
        db.commit()
        return {"status": "EMPTY", "processed": 0}
    if selected.status == "NEW":
        set_status(db, selected, "QUEUED", action="QUEUE_NEW", reason="Scheduler picked new task")
    if apply_delay_if_needed(db, selected, settings):
        db.commit()
        return {"status": "DELAYED", "processed": 1, "task_id": selected.id}
    account, reason = select_account_for_task(db, selected, settings)
    if not account:
        selected.error_message = reason or "No available account"
        set_status(db, selected, "WAITING_ACCOUNT", action="SELECT_ACCOUNT", reason=selected.error_message)
        db.commit()
        return {"status": "WAITING_ACCOUNT", "processed": 1, "task_id": selected.id}
    selected.account_id = account.id
    if (
        selected.task_type in {"REPLY", "REPLY_TASK"}
        and (selected.payload or {}).get("action_type") == "PREPARE_REPLY"
        and not (selected.payload or {}).get("warmup_created")
    ):
        from app.services.engagement import create_reply_warmup_tasks

        warmups = create_reply_warmup_tasks(db, selected)
        selected.payload = {
            **(selected.payload or {}),
            "warmup_created": True,
            "warmup_task_ids": [task.id for task in warmups],
        }
    selected.earliest_execute_at = selected.earliest_execute_at or now
    set_status(db, selected, "READY", action="READY", reason="Account selected", selected_account_id=account.id)
    selected.payload = {
        **(selected.payload or {}),
        "execution_placeholder": "已接收任务，等待未来执行引擎",
        "dispatched_by": "scheduler.run_once",
    }
    set_status(db, selected, "DISPATCHED", action="MOCK_DISPATCH", reason="Execution placeholder only", selected_account_id=account.id)
    execution_task = ExecutionRuntime(db).push_scheduler_task(selected)
    if selected.reply_task_id:
        reply_task = db.get(ReplyTask, selected.reply_task_id)
        if reply_task:
            reply_task.account_id = selected.account_id
            reply_task.execution_task_id = execution_task.id
            reply_task.status = "EXECUTING"
    settings["last_dispatched_platform_id"] = selected.platform_id
    save_scheduler_settings(db, settings)
    db.commit()
    return {
        "status": "DISPATCHED",
        "processed": 1,
        "task_id": selected.id,
        "account_id": account.id,
        "execution_task_id": execution_task.id,
    }


def ensure_platform_weights(db: Session) -> list[PlatformWeight]:
    default_weights = {"reddit": 50, "facebook": 30, "x": 20, "instagram": 15, "tiktok": 10}
    platforms = db.scalars(select(Platform).order_by(Platform.name)).all()
    result = []
    for platform in platforms:
        item = db.scalar(select(PlatformWeight).where(PlatformWeight.platform_id == platform.id))
        if not item:
            item = PlatformWeight(
                platform_id=platform.id,
                weight=default_weights.get(platform.slug, 10),
                enabled=True,
                remark="Seed scheduler platform weight",
            )
            db.add(item)
            db.flush()
        result.append(item)
    return result
