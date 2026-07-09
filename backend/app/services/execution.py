from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    ExecutionLog,
    ExecutionTask,
    Platform,
    ReplayFile,
    SchedulerTask,
    TGEProfile,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def execution_log(
    db: Session,
    task: ExecutionTask,
    action: str,
    *,
    old_status: str | None = None,
    new_status: str | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        ExecutionLog(
            execution_task_id=task.id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            message=message,
            metadata_json=metadata or {},
        )
    )


def set_execution_status(
    db: Session,
    task: ExecutionTask,
    status: str,
    action: str,
    *,
    message: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    old = task.status
    task.status = status
    if status in {"PRECHECKING", "ATTACHING", "PAGE_OPENING"} and not task.started_at:
        task.started_at = utc_now()
    if status in {"SUCCESS", "FAILED", "CANCELLED"}:
        task.finished_at = utc_now()
    if error_code:
        task.error_code = error_code
    if error_message:
        task.error_message = error_message
    execution_log(db, task, action, old_status=old, new_status=status, message=message or error_message)


def profile_for_account(db: Session, account_id: int | None) -> TGEProfile | None:
    if not account_id:
        return None
    return db.scalar(
        select(TGEProfile).where(
            (TGEProfile.bound_account_id == account_id) | (TGEProfile.account_id == account_id)
        )
    )


def create_execution_task_from_scheduler(db: Session, scheduler_task: SchedulerTask) -> ExecutionTask:
    existing = db.scalar(
        select(ExecutionTask).where(ExecutionTask.scheduler_task_id == scheduler_task.id)
    )
    if existing:
        return existing
    platform = db.get(Platform, scheduler_task.platform_id)
    profile = profile_for_account(db, scheduler_task.account_id)
    task = ExecutionTask(
        scheduler_task_id=scheduler_task.id,
        account_id=scheduler_task.account_id,
        tge_profile_id=profile.id if profile else None,
        platform=platform.slug if platform else None,
        action_type=(scheduler_task.payload or {}).get("action_type", "OPEN_PAGE"),
        strategy=(scheduler_task.payload or {}).get("strategy"),
        payload_json=scheduler_task.payload or {},
        status="RECEIVED",
        precheck_status="PENDING",
        environment_status=profile.runtime_status if profile else "UNKNOWN",
    )
    db.add(task)
    db.flush()
    execution_log(db, task, "TASK_RECEIVED", old_status="NEW", new_status="RECEIVED", message="Scheduler task received by Execution.")
    replay = ReplayFile(execution_task_id=task.id)
    db.add(replay)
    return task


def run_precheck(db: Session, task: ExecutionTask) -> ExecutionTask:
    set_execution_status(db, task, "PRECHECKING", "PRECHECK_STARTED")
    account = db.get(Account, task.account_id) if task.account_id else None
    profile = db.get(TGEProfile, task.tge_profile_id) if task.tge_profile_id else None
    if not account:
        task.precheck_status = "FAILED"
        set_execution_status(db, task, "FAILED", "PRECHECK_FAILED", error_code="NO_ACCOUNT", error_message="Execution task has no account")
        return task
    if not profile:
        task.precheck_status = "FAILED"
        set_execution_status(db, task, "FAILED", "PRECHECK_FAILED", error_code="NO_TGE_PROFILE", error_message="Account has no TGE profile binding")
        return task
    if not (profile.tge_environment_id or profile.environment_id):
        task.precheck_status = "FAILED"
        set_execution_status(db, task, "FAILED", "PRECHECK_FAILED", error_code="NO_ENVIRONMENT_ID", error_message="TGE profile has no environment id")
        return task
    if profile.connection_status == "FAILED":
        task.precheck_status = "FAILED"
        set_execution_status(db, task, "FAILED", "PRECHECK_FAILED", error_code="TGE_CONNECTION_FAILED", error_message="TGE profile connection status is FAILED")
        return task
    if (account.risk_status or account.risk_level) in {"HIGH", "CRITICAL"}:
        task.precheck_status = "FAILED"
        set_execution_status(db, task, "FAILED", "PRECHECK_FAILED", error_code="ACCOUNT_RISK_BLOCKED", error_message="Account risk status is not allowed")
        return task
    task.precheck_status = "SUCCESS"
    task.environment_status = profile.runtime_status or "UNKNOWN"
    set_execution_status(db, task, "ENVIRONMENT_READY", "PRECHECK_SUCCESS", message="Execution environment precheck passed")
    return task
