from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    ExecutionQueue,
    ExecutionLog,
    ExecutionTask,
    Platform,
    ReplayFile,
    ReplayIndex,
    SchedulerTask,
    TGEProfile,
    WorkerNode,
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
        status="QUEUED",
        queue_status="QUEUED",
        precheck_status="PENDING",
        environment_status=profile.runtime_status if profile else "UNKNOWN",
    )
    db.add(task)
    db.flush()
    execution_log(db, task, "TASK_QUEUED", old_status="NEW", new_status="QUEUED", message="Scheduler task pushed to Execution queue.")
    replay = ReplayFile(execution_task_id=task.id)
    db.add(replay)
    db.add(ReplayIndex(execution_task_id=task.id, status="INDEXED", artifact_count=0, manifest_json={}))
    existing_queue = db.scalar(
        select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id)
    )
    if not existing_queue:
        db.add(
            ExecutionQueue(
                scheduler_task_id=scheduler_task.id,
                execution_task_id=task.id,
                priority=scheduler_task.priority,
                status="QUEUED",
            )
        )
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


class ExecutionRuntime:
    def __init__(self, db: Session, worker_name: str = "local-worker") -> None:
        self.db = db
        self.worker_name = worker_name

    def register_worker(
        self,
        *,
        host: str = "localhost",
        version: str = "local",
        capability: dict[str, Any] | None = None,
    ) -> WorkerNode:
        worker = self.db.scalar(select(WorkerNode).where(WorkerNode.name == self.worker_name))
        if not worker:
            worker = WorkerNode(
                name=self.worker_name,
                host=host,
                version=version,
                capability=capability or {"mode": "local", "browser_automation": False},
                status="ONLINE",
                last_heartbeat=utc_now(),
            )
            self.db.add(worker)
            self.db.flush()
        else:
            worker.status = "ONLINE"
            worker.host = host or worker.host
            worker.version = version or worker.version
            worker.capability = capability or worker.capability or {}
            worker.last_heartbeat = utc_now()
        return worker

    def heartbeat(self, worker: WorkerNode | None = None) -> WorkerNode:
        worker = worker or self.register_worker()
        worker.status = "ONLINE"
        worker.last_heartbeat = utc_now()
        self.db.flush()
        return worker

    def push_scheduler_task(self, scheduler_task: SchedulerTask) -> ExecutionTask:
        task = create_execution_task_from_scheduler(self.db, scheduler_task)
        queue = self.db.scalar(
            select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id)
        )
        if queue and queue.status not in {"QUEUED", "CLAIMED", "RUNNING", "WAITING_MANUAL", "SUCCESS"}:
            queue.status = "QUEUED"
            queue.error_message = None
        task.status = "QUEUED"
        task.queue_status = "QUEUED"
        execution_log(self.db, task, "QUEUE_PUSHED", new_status="QUEUED", message="Task is waiting for Execution worker.")
        self.db.flush()
        return task

    def claim_next(self, worker: WorkerNode | None = None) -> ExecutionTask | None:
        worker = worker or self.register_worker()
        self.heartbeat(worker)
        queue = self.db.scalar(
            select(ExecutionQueue)
            .where(ExecutionQueue.status == "QUEUED")
            .order_by(ExecutionQueue.priority.asc(), ExecutionQueue.queued_at.asc())
        )
        if not queue:
            return None
        task = self.db.get(ExecutionTask, queue.execution_task_id)
        if not task:
            queue.status = "FAILED"
            queue.error_message = "Execution task missing"
            return None
        now = utc_now()
        queue.status = "CLAIMED"
        queue.worker_node_id = worker.id
        queue.claimed_at = now
        task.status = "CLAIMED"
        task.queue_status = "CLAIMED"
        task.worker_node_id = worker.id
        task.claimed_at = now
        task.last_heartbeat_at = now
        execution_log(self.db, task, "TASK_CLAIMED", old_status="QUEUED", new_status="CLAIMED", message=f"Claimed by {worker.name}")
        return task

    def run_claimed(self, task: ExecutionTask) -> ExecutionTask:
        queue = self.db.scalar(
            select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id)
        )
        now = utc_now()
        if queue:
            queue.status = "RUNNING"
            queue.started_at = now
        task.status = "RUNNING"
        task.queue_status = "RUNNING"
        task.started_at = task.started_at or now
        task.last_heartbeat_at = now
        execution_log(self.db, task, "TASK_RUNNING", old_status="CLAIMED", new_status="RUNNING", message="Local worker started runtime processing without browser automation.")
        return task

    def mark_waiting_manual(self, task: ExecutionTask, message: str = "Waiting for manual operator action") -> ExecutionTask:
        queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id))
        if queue:
            queue.status = "WAITING_MANUAL"
        task.status = "WAITING_MANUAL"
        task.queue_status = "WAITING_MANUAL"
        execution_log(self.db, task, "WAITING_MANUAL", new_status="WAITING_MANUAL", message=message)
        return task

    def complete(self, task: ExecutionTask, *, success: bool = True, message: str | None = None) -> ExecutionTask:
        status = "SUCCESS" if success else "FAILED"
        queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id))
        if queue:
            queue.status = status
            queue.finished_at = utc_now()
            queue.error_message = None if success else message
        set_execution_status(
            self.db,
            task,
            status,
            "EXECUTION_SUCCESS" if success else "EXECUTION_FAILED",
            message=message,
            error_code=None if success else "WORKER_FAILED",
            error_message=None if success else message,
        )
        task.queue_status = status
        scheduler = self.db.get(SchedulerTask, task.scheduler_task_id) if task.scheduler_task_id else None
        if scheduler:
            scheduler.status = "EXECUTED" if success else "FAILED"
            scheduler.error_message = None if success else message
        return task

    def retry(self, task_id: int) -> ExecutionTask:
        task = self.db.get(ExecutionTask, task_id)
        if not task:
            raise ValueError("execution task not found")
        task.retry_count += 1
        task.status = "QUEUED"
        task.queue_status = "QUEUED"
        task.error_code = None
        task.error_message = None
        task.finished_at = None
        queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id))
        if queue:
            queue.status = "QUEUED"
            queue.worker_node_id = None
            queue.claimed_at = None
            queue.started_at = None
            queue.finished_at = None
            queue.error_message = None
        execution_log(self.db, task, "RETRY", new_status="QUEUED", message="Task re-queued without creating a duplicate.")
        return task

    def cancel(self, task_id: int) -> ExecutionTask:
        task = self.db.get(ExecutionTask, task_id)
        if not task:
            raise ValueError("execution task not found")
        queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id))
        if queue:
            queue.status = "CANCELLED"
            queue.finished_at = utc_now()
        set_execution_status(self.db, task, "CANCELLED", "CANCEL", message="Execution task cancelled")
        task.queue_status = "CANCELLED"
        return task

    def resume_manual(self, task_id: int) -> ExecutionTask:
        task = self.db.get(ExecutionTask, task_id)
        if not task:
            raise ValueError("execution task not found")
        if task.status != "WAITING_MANUAL":
            raise ValueError("task is not waiting for manual resume")
        return self.complete(task, success=True, message="Manual step resumed and marked complete.")

    def runtime_status(self) -> dict[str, Any]:
        def count_status(status: str) -> int:
            from sqlalchemy import func

            return self.db.scalar(
                select(func.count()).select_from(ExecutionTask).where(ExecutionTask.status == status)
            ) or 0

        from sqlalchemy import func

        return {
            "runtime": "LOCAL",
            "automation_enabled": False,
            "queue": self.db.scalar(select(func.count()).select_from(ExecutionQueue).where(ExecutionQueue.status == "QUEUED")) or 0,
            "workers": self.db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == "ONLINE")) or 0,
            "running": count_status("RUNNING"),
            "waiting_manual": count_status("WAITING_MANUAL"),
            "success": count_status("SUCCESS"),
            "failed": count_status("FAILED"),
        }
