from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ExecutionTask, ReplayFile, SystemSetting, TGEProfile
from app.services.execution import execution_log, set_execution_status


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
        if self.browser:
            self.browser.close()
        if hasattr(self, "_playwright"):
            self._playwright.stop()
        return {"status": "DISCONNECTED"}


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
