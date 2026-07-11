from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BrowserTab,
    ExecutionQueue,
    ExecutionTask,
    ReplyTask,
    SchedulerTask,
    SubmissionLog,
    SubmissionTask,
    SystemSetting,
)
from app.services.audit import write_audit
from app.services.browser_runtime import BrowserRuntime
from app.services.execution import execution_log, set_execution_status
from app.services.platform_runtime import PlatformRuntime


SUBMISSION_SETTING_KEY = "execution.submission"
DEFAULT_SUBMISSION_SETTINGS: dict[str, Any] = {
    "default_execution_mode": "SEMI_AUTO",
    "auto_assisted_enabled": False,
    "full_auto_enabled": False,
    "max_retry": 1,
    "verify_timeout_seconds": 20,
    "capture_screenshot_enabled": True,
    "capture_html_enabled": True,
}

FINAL_STATUSES = {"VERIFIED", "FAILED", "CANCELLED"}
SUBMISSION_FAILURE_TYPES = {
    "LOGIN_REQUIRED",
    "RATE_LIMITED",
    "SUBMIT_BUTTON_NOT_FOUND",
    "CONTENT_REJECTED",
    "NETWORK_ERROR",
    "PLATFORM_ERROR",
    "VERIFICATION_FAILED",
    "MANUAL_REQUIRED",
    "UNKNOWN_ERROR",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_submission_settings(db: Session) -> dict[str, Any]:
    item = db.scalar(select(SystemSetting).where(SystemSetting.key == SUBMISSION_SETTING_KEY))
    values = {**DEFAULT_SUBMISSION_SETTINGS, **((item.value if item else None) or {})}
    values["default_execution_mode"] = str(values.get("default_execution_mode") or "SEMI_AUTO").upper()
    values["max_retry"] = max(0, int(values.get("max_retry", 1)))
    values["verify_timeout_seconds"] = max(1, int(values.get("verify_timeout_seconds", 20)))
    return values


def save_submission_settings(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    current = get_submission_settings(db)
    merged = {**current, **{key: value for key, value in values.items() if value is not None}}
    merged["default_execution_mode"] = str(merged.get("default_execution_mode") or "SEMI_AUTO").upper()
    if merged["default_execution_mode"] not in {"SEMI_AUTO", "AUTO_ASSISTED", "FULL_AUTO"}:
        merged["default_execution_mode"] = "SEMI_AUTO"
    item = db.scalar(select(SystemSetting).where(SystemSetting.key == SUBMISSION_SETTING_KEY))
    if not item:
        item = SystemSetting(key=SUBMISSION_SETTING_KEY, value=merged, category="execution")
        db.add(item)
    else:
        item.value = merged
        item.category = "execution"
    db.flush()
    return merged


@dataclass
class SubmissionAction:
    allowed: bool
    status: str
    reason: str
    allow_auto_submit: bool = False


class ExecutionPolicyEngine:
    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, execution_mode: str | None) -> SubmissionAction:
        settings = get_submission_settings(self.db)
        mode = str(execution_mode or settings["default_execution_mode"]).upper()
        if mode == "SEMI_AUTO":
            return SubmissionAction(
                allowed=False,
                status="WAITING_MANUAL",
                reason="SEMI_AUTO requires a human to submit on the platform page.",
            )
        if mode == "AUTO_ASSISTED":
            enabled = bool(settings.get("auto_assisted_enabled"))
            return SubmissionAction(
                allowed=enabled,
                status="READY" if enabled else "WAITING_POLICY",
                reason="AUTO_ASSISTED is enabled." if enabled else "AUTO_ASSISTED is disabled by policy.",
                allow_auto_submit=enabled,
            )
        if mode == "FULL_AUTO":
            enabled = bool(settings.get("full_auto_enabled"))
            return SubmissionAction(
                allowed=enabled,
                status="READY" if enabled else "WAITING_POLICY",
                reason="FULL_AUTO is enabled." if enabled else "FULL_AUTO is disabled by policy.",
                allow_auto_submit=enabled,
            )
        return SubmissionAction(False, "WAITING_POLICY", f"Unsupported execution mode: {mode}")


class SubmissionRuntime:
    def __init__(self, db: Session, *, actor: str = "operator", trace_id: str = "system") -> None:
        self.db = db
        self.actor = actor
        self.trace_id = trace_id
        self.policy = ExecutionPolicyEngine(db)

    def get_or_create(
        self,
        *,
        reply_task: ReplyTask | None = None,
        execution: ExecutionTask | None = None,
    ) -> SubmissionTask:
        statement = select(SubmissionTask)
        if reply_task:
            existing = self.db.scalar(statement.where(SubmissionTask.reply_task_id == reply_task.id))
            if existing:
                self._sync_from_sources(existing, reply_task, execution)
                return existing
        if execution:
            existing = self.db.scalar(statement.where(SubmissionTask.execution_task_id == execution.id))
            if existing:
                self._sync_from_sources(existing, reply_task, execution)
                return existing
        task = SubmissionTask(status="CREATED")
        self._sync_from_sources(task, reply_task, execution)
        task.max_retry = get_submission_settings(self.db)["max_retry"]
        self.db.add(task)
        self.db.flush()
        self.log(task, "CREATED", "Submission task created.")
        return task

    def prepare_submission(self, *, reply_task: ReplyTask, execution: ExecutionTask | None = None) -> SubmissionTask:
        task = self.get_or_create(reply_task=reply_task, execution=execution)
        action = self.policy.evaluate(task.execution_mode)
        old_status = task.status
        task.status = action.status
        task.failure_reason = None if action.status != "WAITING_POLICY" else action.reason
        self.log(
            task,
            "WAITING_MANUAL" if task.status == "WAITING_MANUAL" else "WAITING_POLICY",
            action.reason,
            metadata={"execution_mode": task.execution_mode, "auto_submit_allowed": action.allowed},
        )
        if execution:
            execution.payload_json = {
                **(execution.payload_json or {}),
                "submission_task_id": task.id,
                "submission_status": task.status,
                "execution_mode": task.execution_mode,
            }
        self._audit("SubmissionPrepared", task, {"old_status": old_status, "new_status": task.status})
        return task

    def submit_reply(self, submission_task_id: int) -> SubmissionTask:
        task = self._task(submission_task_id)
        action = self.policy.evaluate(task.execution_mode)
        if not action.allowed:
            task.status = action.status
            task.failure_reason = action.reason
            self.log(task, "WAITING_POLICY", action.reason, level="WARNING")
            return task
        adapter = PlatformRuntime(self.db, mock_mode=True).adapter_for(str(task.platform or "unknown"))
        old_status = task.status
        task.status = "SUBMITTING"
        self.log(task, "SUBMITTING", "Submission adapter invoked.", metadata={"mode": task.execution_mode})
        result = adapter.submit_reply(None, allow_auto_submit=action.allow_auto_submit)
        if not result.get("submitted"):
            failure = str(result.get("failure_type") or result.get("code") or "UNKNOWN_ERROR")
            self.capture_failure(task, failure if failure in SUBMISSION_FAILURE_TYPES else "UNKNOWN_ERROR", result)
            self._update_execution_failure(task, failure, str(result.get("reason") or failure))
            return task
        task.submitted_at = utc_now()
        task.status = "SUBMITTED"
        self.log(task, "SUBMITTED", "Submission adapter reported submit action completed.", metadata=result)
        self.verify_success(task)
        self._audit("SubmissionSubmitted", task, {"old_status": old_status, "new_status": task.status})
        return task

    def verify_success(self, task: SubmissionTask) -> SubmissionTask:
        adapter = PlatformRuntime(self.db, mock_mode=True).adapter_for(str(task.platform or "unknown"))
        task.status = "VERIFYING"
        self.log(task, "VERIFYING", "Verification started.")
        reply_task = self.db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
        verified = adapter.verify_reply_success(None, reply_task.reply_content if reply_task else None)
        if not verified.get("verified") and not verified.get("success"):
            self.capture_failure(task, "VERIFICATION_FAILED", verified)
            return task
        url_result = adapter.get_submitted_reply_url(None)
        id_result = adapter.get_submitted_reply_id(None)
        task.status = "VERIFIED"
        task.verified_at = utc_now()
        task.result_url = url_result.get("url")
        task.result_external_id = id_result.get("external_id")
        self.capture_result(task, {"verification": verified, "url": url_result, "external_id": id_result})
        return task

    def record_manual_result(
        self,
        *,
        reply_task: ReplyTask,
        execution: ExecutionTask | None = None,
        scheduler: SchedulerTask | None = None,
    ) -> SubmissionTask:
        task = self.get_or_create(reply_task=reply_task, execution=execution)
        task.manual_confirmed = True
        task.status = "SUBMITTED"
        task.submitted_at = task.submitted_at or utc_now()
        self.log(task, "MANUAL_CONFIRMED", "Human confirmed platform submission.")
        self.verify_success(task)
        if task.status not in FINAL_STATUSES:
            task.status = "VERIFIED"
            task.verified_at = task.verified_at or utc_now()
        if execution:
            payload = execution.payload_json or {}
            execution.payload_json = {
                **payload,
                "manual_confirmed": True,
                "submission_task_id": task.id,
                "submission_status": task.status,
                "result_url": task.result_url,
                "result_external_id": task.result_external_id,
            }
            set_execution_status(
                self.db,
                execution,
                "SUCCESS",
                "SUBMISSION_VERIFIED",
                message="Manual submission recorded by Submission Runtime.",
            )
            execution.queue_status = "SUCCESS"
            queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == execution.id))
            if queue:
                queue.status = "SUCCESS"
                queue.finished_at = utc_now()
            tab_id = task.browser_tab_id or (execution.payload_json or {}).get("browser_tab_id")
            if tab_id:
                BrowserRuntime(self.db).close_tab(int(tab_id))
                self.log(task, "TAB_CLOSED", "Current tab closed after manual confirmation.")
        if scheduler:
            scheduler.status = "EXECUTED"
            scheduler.error_message = None
        reply_task.status = "CONFIRMED"
        self._audit("ManualConfirmed", task, {"reply_task_id": reply_task.id, "execution_task_id": execution.id if execution else None})
        return task

    def capture_result(self, task: SubmissionTask, metadata: dict[str, Any] | None = None) -> None:
        screenshot_path = None
        html_path = None
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        if execution:
            payload = execution.payload_json or {}
            screenshot_path = payload.get("after_fill_screenshot") or payload.get("screenshot_path")
            html_path = payload.get("html_snapshot_path")
        self.log(
            task,
            "RESULT_CAPTURED",
            "Submission result captured.",
            metadata=metadata or {},
            screenshot_path=screenshot_path,
            html_snapshot_path=html_path,
        )

    def capture_failure(self, task: SubmissionTask, failure_type: str, metadata: dict[str, Any] | None = None) -> None:
        task.status = "FAILED"
        task.failure_reason = failure_type
        self.log(task, "SUBMISSION_FAILED", failure_type, level="ERROR", metadata=metadata or {})

    def rollback_if_needed(self, task: SubmissionTask) -> None:
        self.log(task, "ROLLBACK_SKIPPED", "No rollback is available for platform submissions.")

    def dashboard_counts(self) -> dict[str, int]:
        rows = self.db.execute(select(SubmissionTask.status, func.count(SubmissionTask.id)).group_by(SubmissionTask.status)).all()
        counts = {str(status).lower(): int(count) for status, count in rows}
        return {
            "submission_ready": counts.get("ready", 0),
            "submission_waiting_manual": counts.get("waiting_manual", 0),
            "submission_submitting": counts.get("submitting", 0),
            "submission_verified": counts.get("verified", 0),
            "submission_failed": counts.get("failed", 0),
            "submission_manual_required": counts.get("waiting_manual", 0) + counts.get("waiting_policy", 0),
        }

    def log(
        self,
        task: SubmissionTask,
        step: str,
        message: str | None = None,
        *,
        level: str = "INFO",
        metadata: dict[str, Any] | None = None,
        screenshot_path: str | None = None,
        html_snapshot_path: str | None = None,
    ) -> None:
        self.db.add(
            SubmissionLog(
                submission_task_id=task.id,
                step=step,
                level=level,
                message=message,
                metadata_json=metadata or {},
                screenshot_path=screenshot_path,
                html_snapshot_path=html_snapshot_path,
            )
        )

    def _sync_from_sources(
        self,
        task: SubmissionTask,
        reply_task: ReplyTask | None,
        execution: ExecutionTask | None,
    ) -> None:
        payload = execution.payload_json if execution else {}
        if reply_task:
            task.reply_task_id = reply_task.id
            task.platform = reply_task.platform or task.platform
            task.account_id = reply_task.account_id or task.account_id
            task.execution_mode = reply_task.execution_mode or task.execution_mode
        if execution:
            task.execution_task_id = execution.id
            task.platform = execution.platform or task.platform or payload.get("platform")
            task.account_id = execution.account_id or task.account_id or payload.get("account_id")
            task.worker_id = execution.worker_node_id
            task.browser_session_id = payload.get("browser_session_id") or task.browser_session_id
            task.browser_tab_id = payload.get("browser_tab_id") or task.browser_tab_id
            task.execution_mode = str(payload.get("execution_mode") or task.execution_mode or "SEMI_AUTO")
        if task.browser_tab_id and not task.browser_session_id:
            tab = self.db.get(BrowserTab, task.browser_tab_id)
            if tab:
                task.browser_session_id = tab.session_id

    def _update_execution_failure(self, task: SubmissionTask, code: str, message: str) -> None:
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        if not execution:
            return
        set_execution_status(self.db, execution, "FAILED", "SUBMISSION_FAILED", error_code=code, error_message=message)
        execution_log(self.db, execution, "SUBMISSION_RUNTIME_FAILED", new_status="FAILED", message=message)

    def _task(self, task_id: int) -> SubmissionTask:
        task = self.db.get(SubmissionTask, task_id)
        if not task:
            raise ValueError("submission task not found")
        return task

    def _audit(self, action: str, task: SubmissionTask, detail: dict[str, Any] | None = None) -> None:
        write_audit(
            self.db,
            action=action,
            entity_type="SubmissionTask",
            entity_uuid=task.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={"submission_task_id": task.id, **(detail or {})},
        )
