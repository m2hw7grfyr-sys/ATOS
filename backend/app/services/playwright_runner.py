from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Account, AccountLimit, ExecutionLog, ExecutionTask, ReplayFile, SchedulerLog, SchedulerTask, SystemSetting, TGEProfile
from app.services.execution import execution_log, set_execution_status
from app.services.platform_adapter import PlatformAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPLAY_ROOT = PROJECT_ROOT / "storage" / "replay"

DEFAULT_PLAYWRIGHT_SETTINGS = {
    "playwright_enabled": False,
    "playwright_mock_mode": get_settings().playwright_mock_mode,
    "playwright_timeout_seconds": 30,
    "playwright_headless": False,
    "playwright_default_wait_ms": 1000,
    "enable_screenshot": True,
    "enable_html_snapshot": True,
    "enable_auto_close_tab": True,
    "enable_replay_capture": True,
}


def get_playwright_settings(db: Session) -> dict[str, Any]:
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "execution.playwright"))
    values = dict(DEFAULT_PLAYWRIGHT_SETTINGS)
    if setting and setting.value:
        values.update(setting.value)
    return values


def save_playwright_settings(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    values = dict(DEFAULT_PLAYWRIGHT_SETTINGS)
    values.update(payload)
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "execution.playwright"))
    if setting:
        setting.value = values
    else:
        db.add(SystemSetting(key="execution.playwright", category="EXECUTION", value=values))
    db.commit()
    return values


class PlaywrightService:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.browser = None
        self.page = None

    def connect_to_browser(self, websocket_url: str | None):
        if self.settings.get("playwright_mock_mode", True):
            return {"status": "ATTACHED", "mock": True}
        if not websocket_url:
            return {"status": "ATTACH_INFO_MISSING"}
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.connect_over_cdp(websocket_url)
            return {"status": "ATTACHED", "mock": False}
        except Exception as exc:
            return {"status": "ATTACH_FAILED", "message": str(exc)}

    def open_new_tab(self, url: str):
        if self.settings.get("playwright_mock_mode", True):
            self.page = {"url": url}
            return {"status": "PAGE_OPENING", "url": url}
        if not self.browser:
            return {"status": "ATTACH_FAILED", "message": "browser is not connected"}
        context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        self.page = context.new_page()
        self.page.goto(url, timeout=int(self.settings.get("playwright_timeout_seconds", 30)) * 1000)
        return {"status": "PAGE_OPENING", "url": url}

    def wait_for_page_load(self):
        if self.settings.get("playwright_mock_mode", True):
            return {"status": "PAGE_LOADED"}
        self.page.wait_for_load_state("load", timeout=int(self.settings.get("playwright_timeout_seconds", 30)) * 1000)
        return {"status": "PAGE_LOADED"}

    def capture_screenshot(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.settings.get("playwright_mock_mode", True):
            # 1x1 transparent PNG.
            path.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="))
            return {"status": "SCREENSHOT_SAVED", "path": str(path)}
        self.page.screenshot(path=str(path), full_page=True)
        return {"status": "SCREENSHOT_SAVED", "path": str(path)}

    def capture_html(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.settings.get("playwright_mock_mode", True):
            url = self.page.get("url", "") if isinstance(self.page, dict) else ""
            path.write_text(f"<html><body><h1>ATOS Mock Replay</h1><p>{url}</p></body></html>", encoding="utf-8")
            return {"status": "HTML_SAVED", "path": str(path)}
        path.write_text(self.page.content(), encoding="utf-8")
        return {"status": "HTML_SAVED", "path": str(path)}

    def close_current_tab(self):
        if self.settings.get("playwright_mock_mode", True):
            self.page = None
            return {"status": "TAB_CLOSED"}
        if self.page:
            self.page.close()
        return {"status": "TAB_CLOSED"}

    def disconnect(self):
        if self.settings.get("playwright_mock_mode", True):
            return {"status": "DISCONNECTED"}
        if hasattr(self, "_playwright"):
            self._playwright.stop()
        return {"status": "DISCONNECTED"}


def _task_url(task: ExecutionTask) -> str:
    payload = task.payload_json or {}
    return str(payload.get("url") or payload.get("post_url") or payload.get("target_url") or "about:blank")


def _reply_content(db: Session, task: ExecutionTask) -> str:
    payload = task.payload_json or {}
    if payload.get("reply_content"):
        return str(payload["reply_content"])
    scheduler_task = db.get(SchedulerTask, task.scheduler_task_id) if task.scheduler_task_id else None
    if scheduler_task and scheduler_task.reply_id:
        from app.models import Reply

        reply = db.get(Reply, scheduler_task.reply_id)
        if reply:
            return reply.content
    return str(payload.get("draft") or payload.get("comment") or "")


def _replay_for_task(db: Session, task: ExecutionTask) -> ReplayFile:
    replay = db.scalar(select(ReplayFile).where(ReplayFile.execution_task_id == task.id))
    if not replay:
        replay = ReplayFile(execution_task_id=task.id)
        db.add(replay)
        db.flush()
    return replay


def _write_timeline(db: Session, task: ExecutionTask, replay: ReplayFile, replay_dir: Path) -> None:
    logs = db.scalars(
        select(ExecutionLog)
        .where(ExecutionLog.execution_task_id == task.id)
        .order_by(ExecutionLog.created_at.asc())
    ).all()
    replay_dir.mkdir(parents=True, exist_ok=True)
    timeline_path = replay_dir / "timeline.json"
    timeline_path.write_text(
        json.dumps(
            [
                {
                    "action": log.action,
                    "old_status": log.old_status,
                    "new_status": log.new_status,
                    "message": log.message,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    replay.timeline_path = str(timeline_path)


def _update_scheduler_success(db: Session, task: ExecutionTask) -> None:
    if not task.scheduler_task_id:
        return
    scheduler_task = db.get(SchedulerTask, task.scheduler_task_id)
    if not scheduler_task:
        return
    old_status = scheduler_task.status
    scheduler_task.status = "EXECUTED"
    db.add(
        SchedulerLog(
            task_id=scheduler_task.id,
            action="EXECUTION_SUCCESS",
            old_status=old_status,
            new_status="EXECUTED",
            reason="Execution task completed successfully",
            selected_account_id=task.account_id,
        )
    )


def _update_scheduler_failed(db: Session, task: ExecutionTask, reason: str) -> None:
    if not task.scheduler_task_id:
        return
    scheduler_task = db.get(SchedulerTask, task.scheduler_task_id)
    if not scheduler_task:
        return
    old_status = scheduler_task.status
    scheduler_task.status = "FAILED"
    scheduler_task.error_message = reason
    db.add(
        SchedulerLog(
            task_id=scheduler_task.id,
            action="EXECUTION_FAILED",
            old_status=old_status,
            new_status="FAILED",
            reason=reason,
            selected_account_id=task.account_id,
        )
    )


def _update_account_success(db: Session, task: ExecutionTask) -> None:
    if not task.account_id:
        return
    from app.models import utc_now

    account = db.get(Account, task.account_id)
    if not account:
        return
    account.last_active_at = utc_now()
    account.health_score = min(100, (account.health_score or 0) + 1)
    limits = db.scalar(select(AccountLimit).where(AccountLimit.account_id == account.id))
    if limits:
        limits.current_reply_count += 1


def _update_account_failed(db: Session, task: ExecutionTask, reason: str) -> None:
    if not task.account_id:
        return
    account = db.get(Account, task.account_id)
    if not account:
        return
    account.health_score = max(0, (account.health_score or 0) - 5)
    account.failure_count_24h += 1
    account.last_failure_reason = reason


def run_open_page(db: Session, task: ExecutionTask) -> ExecutionTask:
    settings = get_playwright_settings(db)
    profile = db.get(TGEProfile, task.tge_profile_id) if task.tge_profile_id else None
    url = (task.payload_json or {}).get("url") or (task.payload_json or {}).get("post_url")
    if not url:
        url = (task.payload_json or {}).get("target_url", "about:blank")
    service = PlaywrightService(settings)

    set_execution_status(db, task, "ATTACHING", "ATTACH_STARTED")
    attach_info = profile.websocket_url if profile else None
    if not attach_info and profile and profile.debug_port:
        attach_info = f"http://127.0.0.1:{profile.debug_port}"
    attached = service.connect_to_browser(attach_info)
    if attached["status"] == "ATTACH_INFO_MISSING":
        set_execution_status(db, task, "ATTACH_FAILED", "ATTACH_INFO_MISSING", error_code="ATTACH_INFO_MISSING", error_message="Missing websocket_url or debug_port")
        return task
    if attached["status"] == "ATTACH_FAILED":
        set_execution_status(db, task, "ATTACH_FAILED", "ATTACH_FAILED", error_code="ATTACH_FAILED", error_message=str(attached.get("message", "attach failed")))
        return task
    set_execution_status(db, task, "ATTACHED", "ATTACH_SUCCESS", message="Browser attached")

    set_execution_status(db, task, "PAGE_OPENING", "PAGE_OPEN_STARTED", message=str(url))
    service.open_new_tab(str(url))
    loaded = service.wait_for_page_load()
    if loaded["status"] != "PAGE_LOADED":
        set_execution_status(db, task, "PAGE_LOAD_FAILED", "PAGE_LOAD_FAILED", error_code="PAGE_LOAD_FAILED", error_message="Page did not load")
        return task
    set_execution_status(db, task, "PAGE_LOADED", "PAGE_LOAD_SUCCESS")

    replay = db.scalar(select(ReplayFile).where(ReplayFile.execution_task_id == task.id))
    if not replay:
        replay = ReplayFile(execution_task_id=task.id)
        db.add(replay)
        db.flush()
    replay_dir = REPLAY_ROOT / task.uuid
    if settings.get("enable_screenshot", True):
        result = service.capture_screenshot(replay_dir / "screenshot.png")
        replay.screenshot_path = result["path"]
        set_execution_status(db, task, "SCREENSHOT_SAVED", "SCREENSHOT_SAVED")
    if settings.get("enable_html_snapshot", True):
        result = service.capture_html(replay_dir / "page.html")
        replay.html_path = result["path"]
        set_execution_status(db, task, "HTML_SAVED", "HTML_SAVED")
    if settings.get("enable_auto_close_tab", True):
        service.close_current_tab()
        set_execution_status(db, task, "TAB_CLOSED", "TAB_CLOSED")
    service.disconnect()
    set_execution_status(db, task, "SUCCESS", "EXECUTION_SUCCESS")
    execution_log(db, task, "REPLAY_CAPTURED", message="Replay artifact placeholders saved.", metadata={"replay_dir": str(replay_dir)})
    return task


def prepare_reply(db: Session, task: ExecutionTask) -> ExecutionTask:
    settings = get_playwright_settings(db)
    profile = db.get(TGEProfile, task.tge_profile_id) if task.tge_profile_id else None
    service = PlaywrightService(settings)
    platform = task.platform or "reddit"
    adapter = PlatformAdapter(platform, db, mock_mode=bool(settings.get("playwright_mock_mode", True)))
    reply_content = _reply_content(db, task)
    if not reply_content:
        set_execution_status(db, task, "FAILED", "FILL_REPLY_FAILED", error_code="NO_REPLY_CONTENT", error_message="Reply content is missing")
        _update_scheduler_failed(db, task, "Reply content is missing")
        _update_account_failed(db, task, "Reply content is missing")
        return task

    set_execution_status(db, task, "ATTACHING", "ATTACH_STARTED")
    attach_info = profile.websocket_url if profile else None
    if not attach_info and profile and profile.debug_port:
        attach_info = f"http://127.0.0.1:{profile.debug_port}"
    attached = service.connect_to_browser(attach_info)
    if attached["status"] in {"ATTACH_INFO_MISSING", "ATTACH_FAILED"}:
        message = str(attached.get("message") or "Missing websocket_url or debug_port")
        set_execution_status(db, task, "ATTACH_FAILED", attached["status"], error_code=attached["status"], error_message=message)
        _update_scheduler_failed(db, task, message)
        _update_account_failed(db, task, message)
        return task
    set_execution_status(db, task, "ATTACHED", "ATTACH_SUCCESS", message="Browser attached")

    url = _task_url(task)
    set_execution_status(db, task, "PAGE_OPENING", "PAGE_OPEN_STARTED", message=url)
    service.open_new_tab(url)
    service.wait_for_page_load()
    set_execution_status(db, task, "PAGE_LOADED", "PAGE_LOAD_SUCCESS")

    disabled = adapter.detect_comment_disabled(service.page)
    if disabled.get("detected"):
        set_execution_status(db, task, "COMMENT_DISABLED", "COMMENT_DISABLED", error_code="COMMENT_DISABLED", error_message="Commenting is disabled")
        _update_scheduler_failed(db, task, "Commenting is disabled")
        return task
    login_required = adapter.detect_login_required(service.page)
    if login_required.get("detected"):
        set_execution_status(db, task, "LOGIN_REQUIRED", "LOGIN_REQUIRED", error_code="LOGIN_REQUIRED", error_message="Login is required")
        _update_scheduler_failed(db, task, "Login is required")
        return task
    rate_limited = adapter.detect_rate_limited(service.page)
    if rate_limited.get("detected"):
        set_execution_status(db, task, "RATE_LIMITED", "RATE_LIMITED", error_code="RATE_LIMITED", error_message="Platform rate limited this account")
        _update_scheduler_failed(db, task, "Platform rate limited this account")
        return task

    replay = _replay_for_task(db, task)
    replay_dir = REPLAY_ROOT / task.uuid
    if settings.get("enable_screenshot", True):
        before = service.capture_screenshot(replay_dir / "before_fill.png")
        replay.before_fill_screenshot_path = before["path"]

    set_execution_status(db, task, "FINDING_REPLY_BOX", "FIND_REPLY_BOX_STARTED")
    reply_box = adapter.find_reply_box(service.page)
    if not reply_box.get("found"):
        reason = str(reply_box.get("reason") or "Reply box not found")
        set_execution_status(db, task, "COMMENT_BOX_NOT_FOUND", "COMMENT_BOX_NOT_FOUND", error_code="COMMENT_BOX_NOT_FOUND", error_message=reason)
        _update_scheduler_failed(db, task, reason)
        return task
    set_execution_status(db, task, "REPLY_BOX_FOUND", "REPLY_BOX_FOUND")

    adapter.focus_reply_box(service.page, reply_box.get("locator"))
    set_execution_status(db, task, "FILLING_REPLY", "FILL_REPLY_STARTED")
    adapter.fill_reply_box(service.page, reply_box.get("locator"), reply_content)
    set_execution_status(db, task, "REPLY_FILLED", "REPLY_FILLED", message=f"Filled {len(reply_content)} characters")
    if settings.get("enable_screenshot", True):
        after = service.capture_screenshot(replay_dir / "after_fill.png")
        replay.after_fill_screenshot_path = after["path"]
        replay.screenshot_path = after["path"]
    if settings.get("enable_html_snapshot", True):
        html = service.capture_html(replay_dir / "page.html")
        replay.html_path = html["path"]
    _write_timeline(db, task, replay, replay_dir)
    task.payload_json = {
        **(task.payload_json or {}),
        "reply_content_preview": reply_content[:500],
        "fill_status": "REPLY_FILLED",
    }
    set_execution_status(db, task, "WAITING_MANUAL", "WAITING_MANUAL", message="Reply content filled. Waiting for operator to submit manually.")
    service.disconnect()
    return task


def close_execution_tab(db: Session, task: ExecutionTask, *, final_status: str | None = None) -> ExecutionTask:
    settings = get_playwright_settings(db)
    service = PlaywrightService(settings)
    service.close_current_tab()
    set_execution_status(db, task, "TAB_CLOSED", "TAB_CLOSED", message="Current tab closed")
    if final_status:
        set_execution_status(db, task, final_status, "EXECUTION_SUCCESS" if final_status == "SUCCESS" else "EXECUTION_FAILED")
    return task


def mark_submitted(db: Session, task: ExecutionTask) -> ExecutionTask:
    set_execution_status(db, task, "MANUAL_SUBMITTED", "MANUAL_SUBMITTED", message="Operator confirmed platform submit click")
    settings = get_playwright_settings(db)
    adapter = PlatformAdapter(task.platform or "reddit", db, mock_mode=bool(settings.get("playwright_mock_mode", True)))
    detected = adapter.detect_submitted(None)
    task.payload_json = {
        **(task.payload_json or {}),
        "manual_confirmed": True,
        "submission_detected": bool(detected.get("submitted")),
    }
    set_execution_status(db, task, "SUBMISSION_CONFIRMED", "SUBMISSION_CONFIRMED", message="Submission confirmed by operator")
    close_execution_tab(db, task, final_status="SUCCESS")
    _update_scheduler_success(db, task)
    _update_account_success(db, task)
    replay = _replay_for_task(db, task)
    _write_timeline(db, task, replay, REPLAY_ROOT / task.uuid)
    return task
