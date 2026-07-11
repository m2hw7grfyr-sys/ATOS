from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Account,
    AccountAutoSubmitLimit,
    AccountLimit,
    AccountWorkingWindow,
    AutoAssistedPlatformConfig,
    BrowserSession,
    BrowserTab,
    ExecutionQueue,
    ExecutionTask,
    PlatformRegistry,
    Post,
    ReplyTask,
    SchedulerTask,
    SubmissionLog,
    SubmissionTask,
    SystemSetting,
    WorkerNode,
)
from app.services.audit import write_audit
from app.services.browser_runtime import BrowserRuntime
from app.services.execution import execution_log, set_execution_status
from app.services.platform_runtime import PlatformRuntime
from app.services.reply_template_strategy import TemplateSelectionEngine


SUBMISSION_SETTING_KEY = "execution.submission"
DEFAULT_SUBMISSION_SETTINGS: dict[str, Any] = {
    "default_execution_mode": "SEMI_AUTO",
    "auto_assisted_enabled": False,
    "auto_assisted_test_mode": False,
    "full_auto_enabled": False,
    "max_retry": 1,
    "verify_timeout_seconds": 20,
    "capture_screenshot_enabled": True,
    "capture_html_enabled": True,
    "max_reply_retry": 1,
    "max_submission_retry": 1,
    "screenshot_required": True,
    "html_snapshot_on_failure": True,
    "manual_confirm_required": True,
    "verification_level_default": "MANUAL_CONFIRMED",
    "retry_on_browser_disconnect": True,
    "retry_on_worker_offline": True,
    "auto_assisted_real_submit_enabled": False,
    "audit_enabled": True,
    "verification_required": True,
}

SUBMISSION_STATES = {
    "CREATED",
    "PREPARED",
    "SUBMITTING",
    "WAITING_MANUAL",
    "MANUAL_CONFIRMED",
    "VERIFYING",
    "VERIFIED",
    "COMPLETED",
    "FAILED",
    "MANUAL_REQUIRED",
    "MANUAL_REVIEW",
    "RETRY_PENDING",
    "CANCELLED",
    "UNKNOWN",
    "VERIFICATION_FAILED",
}
FINAL_STATUSES = {"VERIFIED", "COMPLETED", "FAILED", "CANCELLED"}
VERIFICATION_LEVELS = {
    "NONE",
    "MANUAL_CONFIRMED",
    "DOM_VERIFIED",
    "URL_VERIFIED",
    "EXTERNAL_ID_VERIFIED",
    "FULL_VERIFIED",
}
SUBMISSION_FAILURE_TYPES = {
    "LOGIN_REQUIRED",
    "REPLY_BOX_NOT_FOUND",
    "EDITOR_NOT_READY",
    "RATE_LIMITED",
    "PAGE_LOAD_FAILED",
    "BROWSER_DISCONNECTED",
    "WORKER_OFFLINE",
    "CONTENT_REJECTED",
    "SUBMISSION_FAILED",
    "VERIFICATION_FAILED",
    "MANUAL_REQUIRED",
    "UNKNOWN_ERROR",
}
NON_RETRYABLE_FAILURES = {"LOGIN_REQUIRED", "RATE_LIMITED", "CONTENT_REJECTED", "MANUAL_REQUIRED"}
ERROR_ALIASES = {
    "X_LOGIN_REQUIRED": "LOGIN_REQUIRED",
    "X_REPLY_BOX_NOT_FOUND": "REPLY_BOX_NOT_FOUND",
    "X_EDITOR_NOT_READY": "EDITOR_NOT_READY",
    "X_RATE_LIMITED": "RATE_LIMITED",
    "X_PAGE_LOAD_FAILED": "PAGE_LOAD_FAILED",
    "X_CONTENT_REJECTED": "CONTENT_REJECTED",
    "X_UNKNOWN_ERROR": "UNKNOWN_ERROR",
    "COMMENT_BOX_NOT_FOUND": "REPLY_BOX_NOT_FOUND",
    "SUBMIT_BUTTON_NOT_FOUND": "SUBMISSION_FAILED",
    "PLATFORM_ERROR": "SUBMISSION_FAILED",
    "NETWORK_ERROR": "BROWSER_DISCONNECTED",
    "NO_ACCOUNT": "MANUAL_REQUIRED",
    "NO_TGE_PROFILE": "MANUAL_REQUIRED",
}
SCREENSHOT_STEPS = [
    "before_open",
    "after_open",
    "before_reply_box",
    "after_reply_box",
    "before_fill",
    "after_fill",
    "waiting_manual",
    "manual_confirmed",
    "failure",
]
HTML_FAILURES = {
    "REPLY_BOX_NOT_FOUND",
    "EDITOR_NOT_READY",
    "PAGE_LOAD_FAILED",
    "SUBMISSION_FAILED",
    "VERIFICATION_FAILED",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_submission_settings(db: Session) -> dict[str, Any]:
    item = db.scalar(select(SystemSetting).where(SystemSetting.key == SUBMISSION_SETTING_KEY))
    values = {**DEFAULT_SUBMISSION_SETTINGS, **((item.value if item else None) or {})}
    values["default_execution_mode"] = str(values.get("default_execution_mode") or "SEMI_AUTO").upper()
    values["max_retry"] = max(0, int(values.get("max_retry", 1)))
    values["max_reply_retry"] = max(0, int(values.get("max_reply_retry", 1)))
    values["max_submission_retry"] = max(0, int(values.get("max_submission_retry", values["max_retry"])))
    values["verify_timeout_seconds"] = max(1, int(values.get("verify_timeout_seconds", 20)))
    values["verification_level_default"] = str(values.get("verification_level_default") or "MANUAL_CONFIRMED").upper()
    if values["verification_level_default"] not in VERIFICATION_LEVELS:
        values["verification_level_default"] = "MANUAL_CONFIRMED"
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


def get_auto_assisted_platform_configs(db: Session) -> list[dict[str, Any]]:
    ensure_default_auto_assisted_platforms(db)
    rows = db.scalars(select(AutoAssistedPlatformConfig).order_by(AutoAssistedPlatformConfig.platform.asc())).all()
    return [
        {
            "id": row.id,
            "uuid": row.uuid,
            "platform": row.platform,
            "auto_assisted_enabled": row.auto_assisted_enabled,
            "max_daily_auto_submit": row.max_daily_auto_submit,
            "allowed_accounts": row.allowed_accounts or [],
            "allowed_time_window": row.allowed_time_window or {},
            "enabled_by": row.enabled_by,
            "enabled_at": row.enabled_at.isoformat() if row.enabled_at else None,
            "remark": row.remark,
            "status": row.status,
        }
        for row in rows
    ]


def ensure_default_auto_assisted_platforms(db: Session) -> None:
    for platform, limit in {"reddit": 3, "x": 3}.items():
        existing = db.scalar(select(AutoAssistedPlatformConfig).where(AutoAssistedPlatformConfig.platform == platform))
        if not existing:
            db.add(
                AutoAssistedPlatformConfig(
                    platform=platform,
                    auto_assisted_enabled=False,
                    max_daily_auto_submit=limit,
                    allowed_accounts=[],
                    allowed_time_window={"allowed_start_time": "09:00", "allowed_end_time": "22:00", "timezone": "Asia/Shanghai"},
                )
            )
    db.flush()


def save_auto_assisted_platform_config(
    db: Session,
    platform: str,
    values: dict[str, Any],
    *,
    actor: str = "operator",
    trace_id: str = "system",
) -> dict[str, Any]:
    platform = platform.lower().strip()
    ensure_default_auto_assisted_platforms(db)
    item = db.scalar(select(AutoAssistedPlatformConfig).where(AutoAssistedPlatformConfig.platform == platform))
    if not item:
        item = AutoAssistedPlatformConfig(platform=platform)
        db.add(item)
    old_enabled = item.auto_assisted_enabled
    if "auto_assisted_enabled" in values:
        item.auto_assisted_enabled = bool(values["auto_assisted_enabled"])
        if item.auto_assisted_enabled and not old_enabled:
            item.enabled_by = actor
            item.enabled_at = utc_now()
    if "max_daily_auto_submit" in values:
        item.max_daily_auto_submit = max(0, int(values["max_daily_auto_submit"] or 0))
    if "allowed_accounts" in values:
        item.allowed_accounts = values.get("allowed_accounts") or []
    if "allowed_time_window" in values:
        item.allowed_time_window = values.get("allowed_time_window") or {}
    if "remark" in values:
        item.remark = values.get("remark")
    db.flush()
    action = "AUTO_ASSISTED Enabled" if item.auto_assisted_enabled and not old_enabled else "AUTO_ASSISTED Disabled" if old_enabled and not item.auto_assisted_enabled else "AUTO_ASSISTED Platform Config Updated"
    write_audit(
        db,
        action=action,
        entity_type="AutoAssistedPlatformConfig",
        entity_uuid=item.uuid,
        actor=actor,
        trace_id=trace_id,
        detail={"platform": platform, "auto_assisted_enabled": item.auto_assisted_enabled},
    )
    return get_auto_assisted_platform_config(db, platform)


def get_auto_assisted_platform_config(db: Session, platform: str) -> dict[str, Any]:
    platform = platform.lower().strip()
    ensure_default_auto_assisted_platforms(db)
    item = db.scalar(select(AutoAssistedPlatformConfig).where(AutoAssistedPlatformConfig.platform == platform))
    if not item:
        return {}
    return {
        "id": item.id,
        "uuid": item.uuid,
        "platform": item.platform,
        "auto_assisted_enabled": item.auto_assisted_enabled,
        "max_daily_auto_submit": item.max_daily_auto_submit,
        "allowed_accounts": item.allowed_accounts or [],
        "allowed_time_window": item.allowed_time_window or {},
        "enabled_by": item.enabled_by,
        "enabled_at": item.enabled_at.isoformat() if item.enabled_at else None,
        "remark": item.remark,
        "status": item.status,
    }


@dataclass
class SubmissionAction:
    allowed: bool
    status: str
    reason: str
    allow_auto_submit: bool = False


class ExecutionPolicyEngine:
    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, execution_mode: str | None, task: SubmissionTask | None = None) -> SubmissionAction:
        settings = get_submission_settings(self.db)
        mode = str(execution_mode or settings["default_execution_mode"]).upper()
        if mode == "SEMI_AUTO":
            return SubmissionAction(
                allowed=False,
                status="WAITING_MANUAL",
                reason="SEMI_AUTO requires a human to submit on the platform page.",
            )
        if mode == "AUTO_ASSISTED":
            checks = self.auto_assisted_checks(task, settings)
            enabled = not checks["blocked"]
            return SubmissionAction(
                allowed=enabled,
                status="READY" if enabled else "WAITING_POLICY",
                reason="AUTO_ASSISTED policy passed." if enabled else checks["reason"],
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

    def auto_assisted_checks(self, task: SubmissionTask | None, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = settings or get_submission_settings(self.db)
        app_settings = get_settings()
        reasons: list[str] = []
        if not bool(settings.get("auto_assisted_enabled")):
            reasons.append("Global AUTO_ASSISTED is disabled")
        if not bool(settings.get("auto_assisted_test_mode")) and not bool(settings.get("auto_assisted_real_submit_enabled")):
            reasons.append("Real AUTO_ASSISTED submit is disabled in this build; enable Test Mode to simulate")
        if app_settings.is_production and app_settings.production_guard_enabled:
            if not app_settings.worker_api_token:
                reasons.append("Production guard: WORKER_API_TOKEN is required")
            if app_settings.debug:
                reasons.append("Production guard: debug mode must be disabled")
            if not settings.get("audit_enabled", True):
                reasons.append("Production guard: audit must be enabled")
            if not settings.get("verification_required", True):
                reasons.append("Production guard: verification must be enabled")
            if not settings.get("screenshot_required", True):
                reasons.append("Production guard: screenshot evidence is required")
        if not task:
            return {"blocked": bool(reasons), "reason": "; ".join(reasons) or "AUTO_ASSISTED policy passed", "reasons": reasons}

        platform = str(task.platform or "").lower()
        reply_task = self.db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
        if not reply_task:
            reasons.append("No approved reply task is linked")
        elif reply_task.status not in {"APPROVED", "SCHEDULED", "EXECUTING", "WAITING_MANUAL", "SUBMITTED", "CONFIRMED"}:
            reasons.append(f"Reply task is not approved: {reply_task.status}")
        elif reply_task.reply_template_id:
            allowed, reason = TemplateSelectionEngine(self.db).auto_assisted_allowed(reply_task)
            if not allowed:
                reasons.append(reason)
        else:
            reasons.append("Reply task has no template; AUTO_ASSISTED requires template risk check")
        platform_config = self.db.scalar(
            select(AutoAssistedPlatformConfig).where(AutoAssistedPlatformConfig.platform == platform)
        )
        if not platform_config or not platform_config.auto_assisted_enabled:
            reasons.append(f"Platform AUTO_ASSISTED is disabled for {platform or 'unknown'}")

        account = self.db.get(Account, task.account_id) if task.account_id else None
        if not account:
            reasons.append("No account bound to submission task")
        elif not account.allow_auto_assisted:
            reasons.append("Account AUTO_ASSISTED permission is disabled")
        elif account.status != "ACTIVE":
            reasons.append("Account is not ACTIVE")
        elif account.risk_status in {"HIGH", "CRITICAL"}:
            reasons.append(f"Account risk_status blocks AUTO_ASSISTED: {account.risk_status}")

        if platform_config and account and platform_config.allowed_accounts:
            allowed = {str(item) for item in platform_config.allowed_accounts}
            if str(account.id) not in allowed and account.username not in allowed and account.uuid not in allowed:
                reasons.append("Account is not in platform allowed_accounts")

        if account and not self._daily_limit_available(account, platform, platform_config):
            reasons.append("Account daily AUTO_ASSISTED limit reached")

        if not self._time_window_allowed(platform_config):
            reasons.append("Outside platform AUTO_ASSISTED time window")

        if not self._platform_supports_auto_submit(platform):
            reasons.append(f"Platform capability AUTO_SUBMIT is not registered for {platform or 'unknown'}")

        worker = self.db.get(WorkerNode, task.worker_id) if task.worker_id else None
        if not worker:
            reasons.append("No worker bound to submission task")
        elif worker.status not in {"ONLINE", "HEALTHY", "READY", "ACTIVE"}:
            reasons.append(f"Worker is not healthy: {worker.status}")

        session = self.db.get(BrowserSession, task.browser_session_id) if task.browser_session_id else None
        if not session:
            reasons.append("No browser session bound to submission task")
        elif session.status not in {"RUNNING", "ATTACHED", "ACTIVE", "READY"}:
            reasons.append(f"Browser session is not normal: {session.status}")

        if not settings.get("screenshot_required", True) or not settings.get("capture_screenshot_enabled", True):
            reasons.append("Screenshot capture is required for AUTO_ASSISTED")

        return {"blocked": bool(reasons), "reason": "; ".join(reasons) or "AUTO_ASSISTED policy passed", "reasons": reasons}

    def _platform_supports_auto_submit(self, platform: str) -> bool:
        if not platform:
            return False
        registry = self.db.scalar(select(PlatformRegistry).where(PlatformRegistry.platform_name == platform))
        if registry and registry.capabilities:
            return bool(registry.capabilities.get("AUTO_SUBMIT"))
        try:
            adapter = PlatformRuntime(self.db, mock_mode=True).adapter_for(platform)
            return "AUTO_SUBMIT" in adapter.capabilities
        except Exception:
            return False

    def _daily_limit_available(
        self,
        account: Account,
        platform: str,
        platform_config: AutoAssistedPlatformConfig | None,
    ) -> bool:
        today = utc_now().date()
        limit = self.db.scalar(
            select(AccountAutoSubmitLimit).where(
                AccountAutoSubmitLimit.account_id == account.id,
                AccountAutoSubmitLimit.platform == platform,
            )
        )
        if not limit:
            limit = AccountAutoSubmitLimit(
                account_id=account.id,
                platform=platform,
                daily_auto_submit_limit=(platform_config.max_daily_auto_submit if platform_config else 3),
                auto_submitted_today=0,
                last_reset_at=utc_now(),
            )
            self.db.add(limit)
            self.db.flush()
        if not limit.last_reset_at or limit.last_reset_at.date() != today:
            limit.auto_submitted_today = 0
            limit.last_reset_at = utc_now()
        max_allowed = min(limit.daily_auto_submit_limit, platform_config.max_daily_auto_submit if platform_config else limit.daily_auto_submit_limit)
        return limit.auto_submitted_today < max_allowed

    def _time_window_allowed(self, platform_config: AutoAssistedPlatformConfig | None) -> bool:
        window = (platform_config.allowed_time_window if platform_config else None) or {}
        start = window.get("allowed_start_time") or window.get("start") or window.get("start_time")
        end = window.get("allowed_end_time") or window.get("end") or window.get("end_time")
        if not start or not end:
            return True
        try:
            zone = ZoneInfo(str(window.get("timezone") or "Asia/Shanghai"))
            current = utc_now().astimezone(zone).strftime("%H:%M")
            return str(start) <= current <= str(end)
        except Exception:
            return True


class FailureRecoveryService:
    def __init__(self, db: Session):
        self.db = db

    def classify(self, error_code: str | None) -> str:
        code = str(error_code or "UNKNOWN_ERROR").upper()
        mapped = ERROR_ALIASES.get(code, code)
        return mapped if mapped in SUBMISSION_FAILURE_TYPES else "UNKNOWN_ERROR"

    def decision(self, task: SubmissionTask, error_code: str | None) -> dict[str, Any]:
        failure_type = self.classify(error_code)
        settings = get_submission_settings(self.db)
        max_retry = int(settings.get("max_submission_retry", 1))
        if failure_type in {"LOGIN_REQUIRED", "RATE_LIMITED"}:
            return {
                "action": "MANUAL_REQUIRED",
                "retryable": False,
                "failure_type": failure_type,
                "reason": f"{failure_type} requires operator intervention.",
            }
        if failure_type == "CONTENT_REJECTED":
            return {
                "action": "FAILED",
                "retryable": False,
                "failure_type": failure_type,
                "reason": "Platform rejected the content; automatic retry is blocked.",
            }
        if failure_type == "VERIFICATION_FAILED":
            return {
                "action": "MANUAL_REVIEW",
                "retryable": False,
                "failure_type": failure_type,
                "reason": "Submission could not be verified; manual review is required.",
            }
        if failure_type == "BROWSER_DISCONNECTED" and settings.get("retry_on_browser_disconnect", True):
            retryable = task.retry_count < max_retry
            return {
                "action": "RETRY_PENDING" if retryable else "FAILED",
                "retryable": retryable,
                "failure_type": failure_type,
                "reason": "Browser disconnected; retry allowed." if retryable else "Retry limit reached.",
            }
        if failure_type == "WORKER_OFFLINE" and settings.get("retry_on_worker_offline", True):
            retryable = task.retry_count < max_retry
            return {
                "action": "RETRY_PENDING" if retryable else "FAILED",
                "retryable": retryable,
                "failure_type": failure_type,
                "reason": "Worker offline; retry allowed." if retryable else "Retry limit reached.",
            }
        return {
            "action": "FAILED",
            "retryable": False,
            "failure_type": failure_type,
            "reason": f"{failure_type} is not automatically recoverable.",
        }


class SubmissionRuntime:
    def __init__(self, db: Session, *, actor: str = "operator", trace_id: str = "system") -> None:
        self.db = db
        self.actor = actor
        self.trace_id = trace_id
        self.policy = ExecutionPolicyEngine(db)
        self.recovery = FailureRecoveryService(db)

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
        task.max_retry = get_submission_settings(self.db)["max_submission_retry"]
        self.db.add(task)
        self.db.flush()
        self.log(task, "CREATED", "Submission task created.")
        return task

    def prepare_submission(self, *, reply_task: ReplyTask, execution: ExecutionTask | None = None) -> SubmissionTask:
        task = self.get_or_create(reply_task=reply_task, execution=execution)
        action = self.policy.evaluate(task.execution_mode, task)
        old_status = task.status
        self.set_status(task, "WAITING_MANUAL" if action.status == "WAITING_MANUAL" else "MANUAL_REQUIRED" if action.status == "WAITING_POLICY" else "PREPARED", reason=action.reason)
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
        action = self.policy.evaluate(task.execution_mode, task)
        self.log(task, "POLICY_CHECKED", action.reason, metadata={"execution_mode": task.execution_mode})
        self._audit("Policy Checked", task, {"policy_result": "PASSED" if action.allowed else "BLOCKED", "reason": action.reason})
        if not action.allowed:
            self.set_status(task, "MANUAL_REQUIRED" if action.status == "WAITING_POLICY" else action.status, reason=action.reason)
            task.failure_reason = action.reason
            self.log(task, "POLICY_BLOCKED", action.reason, level="WARNING")
            self._audit("Policy Blocked", task, {"policy_result": "BLOCKED", "reason": action.reason})
            return task
        settings = get_submission_settings(self.db)
        adapter = PlatformRuntime(self.db, mock_mode=True).adapter_for(str(task.platform or "unknown"))
        old_status = task.status
        self.set_status(task, "SUBMITTING", reason="Auto-assisted submission policy allowed.")
        self.log(task, "AUTO_SUBMIT_STARTED", "Submission adapter invoked.", metadata={"mode": task.execution_mode, "test_mode": settings.get("auto_assisted_test_mode")})
        self._audit("Policy Passed", task, {"old_status": old_status, "new_status": task.status})
        self._audit("Auto Submit Started", task, {"execution_mode": task.execution_mode, "test_mode": settings.get("auto_assisted_test_mode")})
        page = {"test_mode": "submit_success"} if settings.get("auto_assisted_test_mode") else None
        result = adapter.submit_reply(page, allow_auto_submit=action.allow_auto_submit)
        if not result.get("submitted"):
            failure = str(result.get("failure_type") or result.get("code") or "UNKNOWN_ERROR")
            self.capture_failure(task, failure if failure in SUBMISSION_FAILURE_TYPES else "UNKNOWN_ERROR", result)
            self._update_execution_failure(task, failure, str(result.get("reason") or failure))
            self._audit("Manual Fallback", task, {"failure": failure, "reason": result.get("reason")})
            return task
        task.submitted_at = utc_now()
        self.log(task, "AUTO_SUBMIT_COMPLETED", "Submission adapter reported submit action completed.", metadata=result)
        self._audit("Auto Submit Completed", task, result)
        self.verify_success(task)
        if task.status == "VERIFIED":
            self.set_status(task, "COMPLETED", reason="AUTO_ASSISTED submit verified and completed.")
            self._increment_auto_submit(task)
            self._record_template_result(task, submitted=True, verified=True)
        self._audit("SubmissionSubmitted", task, {"old_status": old_status, "new_status": task.status})
        return task

    def verify_success(self, task: SubmissionTask) -> SubmissionTask:
        adapter = PlatformRuntime(self.db, mock_mode=True).adapter_for(str(task.platform or "unknown"))
        self.set_status(task, "VERIFYING", reason="Verification started.")
        self.log(task, "VERIFICATION_STARTED", "Verification started.")
        self._audit("Verification Started", task, {"verification_timeout_seconds": get_submission_settings(self.db).get("verify_timeout_seconds")})
        reply_task = self.db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
        verified = adapter.verify_reply_success(None, reply_task.reply_content if reply_task else None)
        if not verified.get("verified") and not verified.get("success"):
            self.capture_failure(task, "VERIFICATION_FAILED", verified)
            self._audit("Verification Failed", task, verified)
            return task
        url_result = adapter.get_submitted_reply_url(None)
        id_result = adapter.get_submitted_reply_id(None)
        self.set_status(task, "VERIFIED", reason="Verification completed.")
        task.verified_at = utc_now()
        task.result_url = url_result.get("url")
        task.result_external_id = id_result.get("external_id")
        task.verification_level = self._verification_level(task, verified, url_result, id_result)
        task.verification_status = task.verification_level
        self.capture_result(task, {"verification": verified, "url": url_result, "external_id": id_result})
        self._audit("Verification Completed", task, {"verification_level": task.verification_level})
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
        task.operator_id = self.actor
        task.confirmed_at = utc_now()
        self.set_status(task, "MANUAL_CONFIRMED", reason="Human confirmed platform submission.")
        task.submitted_at = task.submitted_at or utc_now()
        self.log(task, "MANUAL_CONFIRMED", "Human confirmed platform submission.")
        self.verify_success(task)
        if task.status not in FINAL_STATUSES:
            self.set_status(task, "MANUAL_CONFIRMED", reason="Manual confirmation recorded without verifiable URL or external ID.")
            task.verified_at = task.verified_at or utc_now()
        if not task.result_url and not task.result_external_id:
            task.verification_level = "MANUAL_CONFIRMED"
            task.verification_status = "MANUAL_CONFIRMED_UNVERIFIED"
        else:
            task.verification_level = task.verification_level or "MANUAL_CONFIRMED"
            task.verification_status = task.verification_status or task.verification_level
        self._record_template_result(task, submitted=True, verified=task.status in {"VERIFIED", "COMPLETED"})
        if execution:
            payload = execution.payload_json or {}
            execution.payload_json = {
                **payload,
                "manual_confirmed": True,
                "submission_task_id": task.id,
                "submission_status": task.status,
                "result_url": task.result_url,
                "result_external_id": task.result_external_id,
                "verification_level": task.verification_level,
                "verification_status": task.verification_status,
            }
            execution_log(
                self.db,
                execution,
                "MANUAL_CONFIRMED",
                new_status="SUCCESS",
                message="Manual Confirmed",
                metadata={
                    "submission_task_id": task.id,
                    "platform": task.platform,
                    "result_url": task.result_url,
                    "result_external_id": task.result_external_id,
                    "verification_level": task.verification_level,
                    "verification_status": task.verification_status,
                },
            )
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
        self._audit("ResultRecorded", task, self.contract(task))
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
        normalized = self.recovery.classify(failure_type)
        task.failure_reason = normalized
        task.error_code = normalized
        task.error_message = str((metadata or {}).get("reason") or normalized)
        decision = self.recovery.decision(task, normalized)
        if decision["action"] == "MANUAL_REQUIRED":
            new_status = "MANUAL_REQUIRED"
        elif decision["action"] == "MANUAL_REVIEW":
            new_status = "MANUAL_REVIEW"
        elif decision["action"] == "RETRY_PENDING":
            new_status = "RETRY_PENDING"
        else:
            new_status = "FAILED"
        self.set_status(task, new_status, reason=decision["reason"], error_code=normalized, error_message=task.error_message)
        self.log(
            task,
            "SUBMISSION_FAILED",
            normalized,
            level="ERROR",
            metadata={**(metadata or {}), "recovery": decision},
            screenshot_path=self.screenshot_path(task, "failure"),
            html_snapshot_path=self.html_snapshot_path(task, normalized),
        )
        self._record_template_result(task, failed=True)

    def mark_failed(self, task_id: int, failure_reason: str) -> SubmissionTask:
        if not failure_reason:
            raise ValueError("failure_reason is required")
        task = self._task(task_id)
        self.capture_failure(task, failure_reason, {"reason": failure_reason, "operator_id": self.actor})
        self._update_related_failed(task)
        self._audit("TaskFailed", task, {"failure_reason": task.failure_reason, "operator_id": self.actor})
        return task

    def retry(self, task_id: int) -> SubmissionTask:
        task = self._task(task_id)
        failure_type = self.recovery.classify(task.error_code or task.failure_reason)
        decision = self.recovery.decision(task, failure_type)
        if not decision["retryable"]:
            task.retry_blocked_reason = decision["reason"]
            self.log(task, "RETRY_BLOCKED", decision["reason"], level="WARNING", metadata=decision)
            self._audit("RetryBlocked", task, decision)
            return task
        task.retry_count += 1
        task.error_code = None
        task.error_message = None
        task.failure_reason = None
        task.retry_blocked_reason = None
        self.set_status(task, "PREPARED", reason="Retry started.")
        self.log(task, "RETRY_STARTED", "Retry started.", metadata=decision)
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        if execution:
            execution.status = "QUEUED"
            execution.queue_status = "QUEUED"
            execution.error_code = None
            execution.error_message = None
        self._audit("RetryStarted", task, decision)
        return task

    def rollback_if_needed(self, task: SubmissionTask) -> None:
        self.log(task, "ROLLBACK_SKIPPED", "No rollback is available for platform submissions.")

    def emergency_stop(self) -> dict[str, Any]:
        settings = save_submission_settings(
            self.db,
            {
                "auto_assisted_enabled": False,
                "full_auto_enabled": False,
                "default_execution_mode": "SEMI_AUTO",
            },
        )
        ensure_default_auto_assisted_platforms(self.db)
        platform_items = self.db.scalars(select(AutoAssistedPlatformConfig)).all()
        for item in platform_items:
            item.auto_assisted_enabled = False
        tasks = self.db.scalars(
            select(SubmissionTask).where(
                SubmissionTask.execution_mode == "AUTO_ASSISTED",
                SubmissionTask.status.in_(["PREPARED", "SUBMITTING", "VERIFYING", "RETRY_PENDING"]),
            )
        ).all()
        for task in tasks:
            self.set_status(task, "WAITING_MANUAL", reason="Emergency Stop disabled AUTO_ASSISTED.")
            self.log(task, "MANUAL_FALLBACK", "Emergency Stop moved task to WAITING_MANUAL.", level="WARNING")
        self._audit_system("AUTO_ASSISTED Disabled", {"reason": "Emergency Stop", "affected_tasks": len(tasks)})
        return {"settings": settings, "affected_tasks": len(tasks)}

    def dashboard_counts(self) -> dict[str, int]:
        rows = self.db.execute(select(SubmissionTask.status, func.count(SubmissionTask.id)).group_by(SubmissionTask.status)).all()
        counts = {str(status).lower(): int(count) for status, count in rows}
        platform_rows = self.db.execute(
            select(SubmissionTask.platform, SubmissionTask.status, func.count(SubmissionTask.id)).group_by(
                SubmissionTask.platform, SubmissionTask.status
            )
        ).all()
        platform_counts: dict[str, dict[str, int]] = {}
        for platform, status, count in platform_rows:
            platform_counts.setdefault(str(platform or "unknown").lower(), {})[str(status).lower()] = int(count)
        return {
            "submission_ready": counts.get("ready", 0),
            "submission_waiting_manual": counts.get("waiting_manual", 0),
            "submission_submitting": counts.get("submitting", 0),
            "submission_verified": counts.get("verified", 0),
            "submission_failed": counts.get("failed", 0),
            "submission_manual_required": counts.get("manual_required", 0),
            "auto_assisted_submitting": counts.get("submitting", 0),
            "auto_assisted_completed": counts.get("completed", 0),
            "auto_assisted_manual_review": counts.get("manual_review", 0),
            "reddit_waiting_manual": platform_counts.get("reddit", {}).get("waiting_manual", 0),
            "x_waiting_manual": platform_counts.get("x", {}).get("waiting_manual", 0),
            "reddit_failed": platform_counts.get("reddit", {}).get("failed", 0),
            "x_failed": platform_counts.get("x", {}).get("failed", 0),
            "manual_confirmed_today": counts.get("manual_confirmed", 0) + counts.get("verified", 0),
            "retry_pending": counts.get("retry_pending", 0),
        }

    def submission_statistics(self) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(SubmissionTask.platform, SubmissionTask.status, func.count(SubmissionTask.id)).group_by(
                SubmissionTask.platform, SubmissionTask.status
            )
        ).all()
        by_platform: dict[str, dict[str, Any]] = {}
        for platform, status, count in rows:
            key = str(platform or "unknown").lower()
            item = by_platform.setdefault(
                key,
                {
                    "platform": key,
                    "filled_count": 0,
                    "manual_confirmed_count": 0,
                    "verified_count": 0,
                    "failed_count": 0,
                    "manual_required_count": 0,
                    "auto_submit_attempts": 0,
                    "auto_submit_success": 0,
                    "verification_success": 0,
                    "verification_failed": 0,
                    "manual_fallback": 0,
                    "policy_blocked": 0,
                    "retry_count": 0,
                },
            )
            status_key = str(status or "").upper()
            if status_key in {"SUBMITTING", "VERIFYING", "VERIFIED", "COMPLETED", "FAILED", "MANUAL_REQUIRED", "MANUAL_REVIEW"}:
                item["auto_submit_attempts"] += int(count)
            if status_key in {"VERIFIED", "COMPLETED"}:
                item["auto_submit_success"] += int(count)
                item["verification_success"] += int(count)
            if status_key in {"VERIFICATION_FAILED", "MANUAL_REVIEW"}:
                item["verification_failed"] += int(count)
            if status_key in {"WAITING_MANUAL", "MANUAL_REQUIRED"}:
                item["manual_fallback"] += int(count)
            if status_key == "MANUAL_REQUIRED":
                item["policy_blocked"] += int(count)
            if status_key in {"WAITING_MANUAL", "MANUAL_CONFIRMED", "VERIFIED"}:
                item["filled_count"] += int(count)
            if status_key in {"MANUAL_CONFIRMED", "VERIFIED"}:
                item["manual_confirmed_count"] += int(count)
            if status_key == "VERIFIED":
                item["verified_count"] += int(count)
            if status_key == "FAILED":
                item["failed_count"] += int(count)
            if status_key == "MANUAL_REQUIRED":
                item["manual_required_count"] += int(count)
        retry_rows = self.db.execute(
            select(SubmissionTask.platform, func.coalesce(func.sum(SubmissionTask.retry_count), 0)).group_by(SubmissionTask.platform)
        ).all()
        for platform, retry_count in retry_rows:
            key = str(platform or "unknown").lower()
            if key in by_platform:
                by_platform[key]["retry_count"] = int(retry_count or 0)
        for item in by_platform.values():
            total = max(item["filled_count"], 1)
            item["success_rate"] = round((item["verified_count"] / total) * 100, 2)
            item["failure_rate"] = round((item["failed_count"] / total) * 100, 2)
            attempts = max(item["auto_submit_attempts"], 1)
            item["fallback_rate"] = round((item["manual_fallback"] / attempts) * 100, 2)
        return list(by_platform.values())

    def failures(self) -> list[dict[str, Any]]:
        tasks = self.db.scalars(
            select(SubmissionTask)
            .where(SubmissionTask.status.in_(["FAILED", "MANUAL_REQUIRED"]))
            .order_by(SubmissionTask.updated_at.desc())
            .limit(100)
        ).all()
        return [self.contract(task) for task in tasks]

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

    def set_status(
        self,
        task: SubmissionTask,
        status: str,
        *,
        reason: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        status = status.upper()
        if status not in SUBMISSION_STATES:
            status = "UNKNOWN"
        old_status = task.status
        task.status = status
        if error_code:
            task.error_code = self.recovery.classify(error_code)
        if error_message:
            task.error_message = error_message
        self.log(
            task,
            f"STATUS_{status}",
            reason or f"{old_status} -> {status}",
            metadata={"old_status": old_status, "new_status": status, "error_code": task.error_code},
        )

    def contract(self, task: SubmissionTask) -> dict[str, Any]:
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        reply_task = self.db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
        post = self.db.get(Post, task.post_id or (reply_task.post_id if reply_task else None)) if (task.post_id or (reply_task and reply_task.post_id)) else None
        payload = execution.payload_json if execution else {}
        return {
            "platform": task.platform,
            "post_url": post.url if post else payload.get("post_url") or payload.get("url"),
            "external_post_id": post.source_post_id if post else payload.get("external_post_id"),
            "reply_task_id": task.reply_task_id,
            "execution_task_id": task.execution_task_id,
            "submission_task_id": task.id,
            "browser_session_id": task.browser_session_id,
            "browser_tab_id": task.browser_tab_id,
            "status": task.status,
            "error_code": task.error_code,
            "error_message": task.error_message,
            "screenshots": self.screenshots(task),
            "metadata": {
                **(task.metadata_json or {}),
                "account_id": task.account_id,
                "operator_id": task.operator_id,
                "confirmed_at": task.confirmed_at.isoformat() if task.confirmed_at else None,
                "verification_level": task.verification_level,
                "verification_status": task.verification_status,
                "result_url": task.result_url,
                "external_reply_id": task.result_external_id,
            },
        }

    def screenshots(self, task: SubmissionTask) -> dict[str, str]:
        return {step: self.screenshot_path(task, step) for step in SCREENSHOT_STEPS}

    def screenshot_path(self, task: SubmissionTask, step: str) -> str:
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        base_uuid = execution.uuid if execution else task.uuid
        return f"storage/replay/{base_uuid}/{task.platform or 'platform'}_{step}.png"

    def html_snapshot_path(self, task: SubmissionTask, failure_type: str | None = None) -> str | None:
        if failure_type and failure_type not in HTML_FAILURES:
            return None
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        base_uuid = execution.uuid if execution else task.uuid
        suffix = (failure_type or "snapshot").lower()
        return f"storage/replay/{base_uuid}/{task.platform or 'platform'}_{suffix}.html"

    def _verification_level(
        self,
        task: SubmissionTask,
        verified: dict[str, Any],
        url_result: dict[str, Any],
        id_result: dict[str, Any],
    ) -> str:
        if verified.get("dom_verified"):
            return "DOM_VERIFIED"
        if url_result.get("url") and id_result.get("external_id"):
            return "EXTERNAL_ID_VERIFIED"
        if url_result.get("url"):
            return "URL_VERIFIED"
        if task.manual_confirmed:
            return "MANUAL_CONFIRMED"
        return get_submission_settings(self.db).get("verification_level_default", "MANUAL_CONFIRMED")

    def _update_related_failed(self, task: SubmissionTask) -> None:
        reply_task = self.db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
        if reply_task:
            reply_task.status = "FAILED" if task.status == "FAILED" else reply_task.status
        execution = self.db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
        if execution:
            set_execution_status(
                self.db,
                execution,
                "FAILED" if task.status == "FAILED" else "WAITING_MANUAL",
                "TASK_FAILED" if task.status == "FAILED" else "MANUAL_REQUIRED",
                error_code=task.error_code,
                error_message=task.error_message or task.failure_reason,
            )
        if execution and execution.scheduler_task_id:
            scheduler = self.db.get(SchedulerTask, execution.scheduler_task_id)
            if scheduler and task.status == "FAILED":
                scheduler.status = "FAILED"
                scheduler.error_message = task.error_message or task.failure_reason

    def _sync_from_sources(
        self,
        task: SubmissionTask,
        reply_task: ReplyTask | None,
        execution: ExecutionTask | None,
    ) -> None:
        payload = execution.payload_json if execution else {}
        if reply_task:
            task.reply_task_id = reply_task.id
            task.post_id = reply_task.post_id or task.post_id
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

    def _increment_auto_submit(self, task: SubmissionTask) -> None:
        if not task.account_id or not task.platform:
            return
        platform = str(task.platform).lower()
        limit = self.db.scalar(
            select(AccountAutoSubmitLimit).where(
                AccountAutoSubmitLimit.account_id == task.account_id,
                AccountAutoSubmitLimit.platform == platform,
            )
        )
        if not limit:
            limit = AccountAutoSubmitLimit(
                account_id=task.account_id,
                platform=platform,
                daily_auto_submit_limit=3,
                auto_submitted_today=0,
                last_reset_at=utc_now(),
            )
            self.db.add(limit)
        if not limit.last_reset_at or limit.last_reset_at.date() != utc_now().date():
            limit.auto_submitted_today = 0
            limit.last_reset_at = utc_now()
        limit.auto_submitted_today += 1
        self.log(task, "AUTO_SUBMIT_LIMIT_UPDATED", "Account daily AUTO_ASSISTED counter incremented.", metadata={"auto_submitted_today": limit.auto_submitted_today})

    def _record_template_result(self, task: SubmissionTask, *, submitted: bool = False, verified: bool = False, failed: bool = False) -> None:
        reply_task = self.db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
        if not reply_task:
            return
        engine = TemplateSelectionEngine(self.db)
        if submitted:
            engine.record_performance(reply_task, "submitted_count")
        if verified:
            engine.record_performance(reply_task, "verified_count")
        if failed:
            engine.record_performance(reply_task, "failed_count")

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

    def _audit_system(self, action: str, detail: dict[str, Any] | None = None) -> None:
        write_audit(
            self.db,
            action=action,
            entity_type="SubmissionRuntime",
            entity_uuid="system",
            actor=self.actor,
            trace_id=self.trace_id,
            detail=detail or {},
        )
