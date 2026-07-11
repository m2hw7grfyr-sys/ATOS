from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AITask,
    Account,
    AccountLimit,
    ExecutionQueue,
    ExecutionTask,
    Platform,
    Post,
    Reply,
    ReplyTask,
    SchedulerTask,
)
from app.services.audit import write_audit
from app.services.browser_runtime import BrowserRuntime
from app.services.execution import ExecutionRuntime, execution_log, profile_for_account, run_precheck, set_execution_status, utc_now
from app.services.platform_runtime import PlatformCapabilityError, PlatformRuntime
from app.services.scheduler import set_status
from app.services.submission_runtime import SubmissionRuntime


EXECUTION_MODE_SEMI_AUTO = "SEMI_AUTO"
EXECUTION_MODE_AUTO_ASSISTED = "AUTO_ASSISTED"
EXECUTION_MODE_FULL_AUTO = "FULL_AUTO"
ALLOWED_EXECUTION_MODES = {
    EXECUTION_MODE_SEMI_AUTO,
    EXECUTION_MODE_AUTO_ASSISTED,
    EXECUTION_MODE_FULL_AUTO,
}


class ReplyPipelineService:
    def __init__(self, db: Session, *, actor: str = "operator", trace_id: str = "system") -> None:
        self.db = db
        self.actor = actor
        self.trace_id = trace_id

    def create_reply_task(
        self,
        *,
        reply_id: int,
        account_id: int | None = None,
        execution_mode: str = EXECUTION_MODE_SEMI_AUTO,
        status: str = "CREATED",
    ) -> ReplyTask:
        execution_mode = execution_mode.upper()
        if execution_mode not in ALLOWED_EXECUTION_MODES:
            raise ValueError("unsupported execution_mode")
        if execution_mode != EXECUTION_MODE_SEMI_AUTO:
            status = "CREATED"
        reply = self.db.get(Reply, reply_id)
        if not reply:
            raise ValueError("reply not found")
        post = self.db.get(Post, reply.post_id)
        if not post:
            raise ValueError("post not found")
        platform = self.db.get(Platform, post.platform_id) if post.platform_id else None
        existing = self.db.scalar(
            select(ReplyTask).where(
                ReplyTask.reply_id == reply.id,
                ReplyTask.status.in_(
                    ["CREATED", "APPROVED", "SCHEDULED", "EXECUTING", "WAITING_MANUAL", "SUBMITTED"]
                ),
            )
        )
        if existing:
            if account_id:
                existing.account_id = account_id
            existing.reply_content = reply.content
            existing.execution_mode = execution_mode
            return existing
        task = ReplyTask(
            post_id=post.id,
            reply_id=reply.id,
            platform=platform.slug if platform else None,
            account_id=account_id,
            reply_content=reply.content,
            execution_mode=execution_mode,
            status=status,
        )
        self.db.add(task)
        self.db.flush()
        self._audit("ReplyTaskCreated", task, {"reply_id": reply.id, "post_id": post.id})
        return task

    def approve_reply(
        self,
        *,
        reply_id: int,
        account_id: int | None = None,
        execution_mode: str = EXECUTION_MODE_SEMI_AUTO,
    ) -> ReplyTask:
        reply = self.db.get(Reply, reply_id)
        if not reply:
            raise ValueError("reply not found")
        reply.status = "APPROVED"
        if reply.ai_task_id:
            ai_task = self.db.get(AITask, reply.ai_task_id)
            if ai_task:
                ai_task.status = "APPROVED"
        task = self.create_reply_task(
            reply_id=reply.id,
            account_id=account_id,
            execution_mode=execution_mode,
            status="APPROVED",
        )
        task.status = "APPROVED"
        task.reply_content = reply.content
        self._audit("ReplyApproved", task, {"reply_id": reply.id, "execution_mode": execution_mode})
        return task

    def schedule_reply_task(
        self,
        reply_task_id: int,
        *,
        account_id: int | None = None,
        priority: str = "MEDIUM",
        source: str = "REPLY_PIPELINE",
    ) -> SchedulerTask:
        reply_task = self._reply_task(reply_task_id)
        reply = self.db.get(Reply, reply_task.reply_id)
        post = self.db.get(Post, reply_task.post_id)
        if not reply or not post:
            raise ValueError("reply task is missing reply or post")
        existing = self.db.scalar(
            select(SchedulerTask).where(
                SchedulerTask.reply_task_id == reply_task.id,
                SchedulerTask.status.in_(["NEW", "QUEUED", "DELAYED", "READY", "DISPATCHED"]),
            )
        )
        if existing:
            return existing
        selected_account_id = account_id or reply_task.account_id
        payload = self.execution_payload(
            reply_task,
            post=post,
            account_id=selected_account_id,
            metadata={"reply_id": reply.id, "reply_task_id": reply_task.id},
        )
        scheduler_task = SchedulerTask(
            task_type="REPLY_TASK",
            platform_id=post.platform_id,
            account_id=selected_account_id,
            post_id=post.id,
            ai_task_id=reply.ai_task_id,
            reply_id=reply.id,
            reply_task_id=reply_task.id,
            source=source,
            priority=priority.upper(),
            payload=payload,
            status="NEW",
        )
        self.db.add(scheduler_task)
        self.db.flush()
        set_status(self.db, scheduler_task, "QUEUED", action="REPLY_TASK_QUEUED", reason="Approved reply task queued")
        reply_task.scheduler_task_id = scheduler_task.id
        reply_task.status = "SCHEDULED"
        if selected_account_id:
            reply_task.account_id = selected_account_id
        self._audit("ReplyScheduled", reply_task, {"scheduler_task_id": scheduler_task.id})
        return scheduler_task

    def create_execution_task(self, reply_task_id: int) -> ExecutionTask:
        reply_task = self._reply_task(reply_task_id)
        scheduler_task = self.db.get(SchedulerTask, reply_task.scheduler_task_id) if reply_task.scheduler_task_id else None
        if not scheduler_task:
            scheduler_task = self.schedule_reply_task(reply_task.id)
        scheduler_task.payload = {
            **(scheduler_task.payload or {}),
            "reply_task_id": reply_task.id,
            "action_type": "PREPARE_REPLY",
        }
        if scheduler_task.status not in {"DISPATCHED", "EXECUTED"}:
            set_status(self.db, scheduler_task, "DISPATCHED", action="REPLY_DISPATCH", reason="Reply task dispatched to Execution")
        execution = ExecutionRuntime(self.db).push_scheduler_task(scheduler_task)
        execution.reply_task_id = reply_task.id
        execution.payload_json = {
            **(execution.payload_json or {}),
            **(scheduler_task.payload or {}),
            "reply_task_id": reply_task.id,
            "task_type": "PREPARE_REPLY",
            "action_type": "PREPARE_REPLY",
        }
        reply_task.execution_task_id = execution.id
        reply_task.status = "EXECUTING"
        self._audit("ExecutionStarted", reply_task, {"execution_task_id": execution.id})
        return execution

    def prepare_reply(self, reply_task_id: int) -> ReplyTask:
        reply_task = self._reply_task(reply_task_id)
        execution = (
            self.db.get(ExecutionTask, reply_task.execution_task_id)
            if reply_task.execution_task_id
            else self.create_execution_task(reply_task.id)
        )
        payload = execution.payload_json or {}
        browser_type = str(payload.get("browser_type") or "mock")
        if execution.precheck_status != "SUCCESS":
            if browser_type == "mock" and execution.account_id and not execution.tge_profile_id:
                execution.precheck_status = "SUCCESS"
                execution.environment_status = "MOCK"
                set_execution_status(
                    self.db,
                    execution,
                    "ENVIRONMENT_READY",
                    "PRECHECK_MOCK_SUCCESS",
                    message="Mock Browser Runtime enabled; TGE profile not required.",
                )
            else:
                run_precheck(self.db, execution)
            if execution.status == "FAILED":
                reply_task.status = "FAILED"
                self._audit("ExecutionFailed", reply_task, {"error": execution.error_message})
                return reply_task
        url = str(payload.get("url") or payload.get("post_url") or payload.get("target_url") or "about:blank")
        platform_key = str(payload.get("platform") or reply_task.platform or execution.platform or "unknown")
        runtime = PlatformRuntime(self.db, mock_mode=True)
        try:
            capability = runtime.assert_capability(platform_key, payload.get("action_type") or "PREPARE_REPLY")
        except PlatformCapabilityError as exc:
            reply_task.status = "FAILED"
            execution.payload_json = {
                **payload,
                "platform": platform_key,
                "action_type": payload.get("action_type") or "PREPARE_REPLY",
                "capability_required": runtime.required_capability(payload.get("action_type") or "PREPARE_REPLY"),
            }
            set_execution_status(
                self.db,
                execution,
                "FAILED",
                "PLATFORM_CAPABILITY_REJECTED",
                error_code="PLATFORM_CAPABILITY_UNSUPPORTED",
                error_message=str(exc),
            )
            return reply_task
        tab = BrowserRuntime(self.db).open_url(
            url=url,
            browser_type=browser_type,
            worker_id=execution.worker_node_id,
            account_id=execution.account_id,
            profile_id=execution.tge_profile_id,
            execution_task_id=execution.id,
        )
        adapter = runtime.adapter_for(platform_key)
        adapter.open_post(None, url)
        login = adapter.detect_login_required(None)
        limited = adapter.detect_rate_limit(None)
        if login.get("detected") or limited.get("detected"):
            reason = "Login required" if login.get("detected") else "Rate limited"
            reply_task.status = "FAILED"
            set_execution_status(self.db, execution, "FAILED", "PREPARE_REPLY_BLOCKED", error_code="PLATFORM_BLOCKED", error_message=reason)
            return reply_task
        reply_box = adapter.find_reply_box(None)
        if not reply_box.get("found"):
            reply_task.status = "FAILED"
            set_execution_status(self.db, execution, "FAILED", "COMMENT_BOX_NOT_FOUND", error_code="COMMENT_BOX_NOT_FOUND", error_message=str(reply_box.get("reason")))
            return reply_task
        adapter.focus_reply_box(None, reply_box)
        filled = adapter.fill_reply(None, reply_task.reply_content)
        now = utc_now()
        execution.payload_json = {
            **payload,
            "platform": platform_key,
            "action_type": payload.get("action_type") or "PREPARE_REPLY",
            "capability_required": capability["capability_required"],
            "browser_tab_id": tab.id,
            "browser_session_id": tab.session_id,
            "fill_status": "REPLY_FILLED" if filled.get("filled") else "FILL_FAILED",
            "reply_content": reply_task.reply_content,
            "reply_content_preview": reply_task.reply_content[:240],
            "before_fill_screenshot": f"storage/replay/{execution.uuid}/before_fill.png",
            "after_fill_screenshot": f"storage/replay/{execution.uuid}/after_fill.png",
            "execution_timeline": ["OPEN_POST", "FIND_REPLY_BOX", "FILL_REPLY", "WAITING_MANUAL"],
            "waiting_manual_message": "Reply prepared. Waiting for manual confirmation.",
        }
        set_execution_status(
            self.db,
            execution,
            "WAITING_MANUAL",
            "REPLY_FILLED",
            message="Reply prepared. Waiting for manual confirmation.",
        )
        execution.started_at = execution.started_at or now
        reply_task.execution_task_id = execution.id
        reply_task.scheduler_task_id = execution.scheduler_task_id or reply_task.scheduler_task_id
        reply_task.status = "WAITING_MANUAL"
        self._queue_status(execution, "WAITING_MANUAL")
        execution_log(self.db, execution, "WAITING_MANUAL", new_status="WAITING_MANUAL", message="Reply content filled into platform editor.")
        SubmissionRuntime(self.db, actor=self.actor, trace_id=self.trace_id).prepare_submission(
            reply_task=reply_task,
            execution=execution,
        )
        self._audit("ReplyFilled", reply_task, {"execution_task_id": execution.id, "tab_id": tab.id})
        return reply_task

    def confirm(self, reply_task_id: int) -> ReplyTask:
        reply_task = self._reply_task(reply_task_id)
        execution = self.db.get(ExecutionTask, reply_task.execution_task_id) if reply_task.execution_task_id else None
        scheduler = self.db.get(SchedulerTask, reply_task.scheduler_task_id) if reply_task.scheduler_task_id else None
        reply_task.status = "SUBMITTED"
        SubmissionRuntime(self.db, actor=self.actor, trace_id=self.trace_id).record_manual_result(
            reply_task=reply_task,
            execution=execution,
            scheduler=scheduler,
        )
        self._update_account_success(reply_task.account_id or (execution.account_id if execution else None))
        reply_task.status = "CONFIRMED"
        self._audit("ManualConfirmed", reply_task, {"execution_task_id": execution.id if execution else None})
        return reply_task

    def execution_payload(
        self,
        reply_task: ReplyTask,
        *,
        post: Post,
        account_id: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = profile_for_account(self.db, account_id)
        return {
            "task_type": "PREPARE_REPLY",
            "action_type": "PREPARE_REPLY",
            "platform": reply_task.platform,
            "url": post.url,
            "post_url": post.url,
            "account_id": account_id,
            "tge_profile_id": profile.id if profile else None,
            "reply_content": reply_task.reply_content,
            "execution_mode": reply_task.execution_mode,
            "capability_required": "REPLY",
            "metadata": metadata or {},
        }

    def _reply_task(self, reply_task_id: int) -> ReplyTask:
        task = self.db.get(ReplyTask, reply_task_id)
        if not task:
            raise ValueError("reply task not found")
        return task

    def _queue_status(self, execution: ExecutionTask, status: str) -> None:
        queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == execution.id))
        if queue:
            queue.status = status
            if status == "SUCCESS":
                queue.finished_at = utc_now()

    def _update_account_success(self, account_id: int | None) -> None:
        if not account_id:
            return
        account = self.db.get(Account, account_id)
        if account:
            account.last_active_at = utc_now()
            account.health_score = min(100, (account.health_score or 0) + 1)
        limits = self.db.scalar(select(AccountLimit).where(AccountLimit.account_id == account_id))
        if limits:
            limits.current_reply_count += 1

    def _audit(self, action: str, task: ReplyTask, detail: dict[str, Any] | None = None) -> None:
        write_audit(
            self.db,
            action=action,
            entity_type="ReplyTask",
            entity_uuid=task.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={"reply_task_id": task.id, **(detail or {})},
        )
