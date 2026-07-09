from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting, TGEProfile


DEFAULT_TGE_SETTINGS = {
    "tge_api_base_url": "",
    "tge_api_key": "",
    "default_timeout_seconds": 10,
    "enable_tge_connection_test": False,
    "enable_auto_start_environment": False,
    "enable_auto_attach_environment": False,
    "enable_auto_close_tab": True,
    "remark": "TGE adapter scaffold. v0.7 supports OPEN_PAGE only.",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def get_tge_settings(db: Session) -> dict[str, Any]:
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "execution.tge"))
    values = dict(DEFAULT_TGE_SETTINGS)
    if setting and setting.value:
        values.update(setting.value)
    return values


def save_tge_settings(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    current = get_tge_settings(db)
    if not payload.get("tge_api_key"):
        payload.pop("tge_api_key", None)
    current.update(payload)
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "execution.tge"))
    if setting:
        setting.value = current
        setting.is_secret = True
    else:
        db.add(SystemSetting(key="execution.tge", category="EXECUTION", value=current, is_secret=True))
    db.commit()
    return safe_tge_settings(current)


def safe_tge_settings(values: dict[str, Any]) -> dict[str, Any]:
    result = dict(values)
    key = result.pop("tge_api_key", "")
    result["tge_api_key_configured"] = bool(key)
    result["tge_api_key_masked"] = mask_secret(key)
    return result


class TgeService:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings

    def _request(self, path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
        base_url = str(self.settings.get("tge_api_base_url") or "").rstrip("/")
        if not base_url:
            return {"status": "UNKNOWN_ERROR", "message": "TGE API base URL is not configured"}
        url = f"{base_url}{path}"
        headers = {"Content-Type": "application/json"}
        api_key = self.settings.get("tge_api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = str(api_key)
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8") if body else None,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=int(self.settings.get("default_timeout_seconds", 10))) as response:
                payload = response.read().decode("utf-8")
            data = json.loads(payload) if payload else {}
            return {"status": "SUCCESS", "data": data}
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return {"status": "UNAUTHORIZED", "message": "TGE API unauthorized"}
            if exc.code == 404:
                return {"status": "NOT_FOUND", "message": "TGE endpoint or profile not found"}
            return {"status": "FAILED", "message": f"TGE HTTP {exc.code}"}
        except TimeoutError:
            return {"status": "TIMEOUT", "message": "TGE API timeout"}
        except urllib.error.URLError as exc:
            return {"status": "FAILED", "message": str(exc.reason)}
        except Exception as exc:
            return {"status": "UNKNOWN_ERROR", "message": str(exc)}

    def test_connection(self) -> dict[str, Any]:
        if not self.settings.get("enable_tge_connection_test"):
            return {"status": "SUCCESS", "message": "Connection test disabled; scaffold ready."}
        return self._request("/health")

    def get_profile_status(self, tge_environment_id: str) -> dict[str, Any]:
        if not self.settings.get("enable_tge_connection_test"):
            return {"status": "SUCCESS", "runtime_status": "UNKNOWN", "message": "Status check scaffold."}
        return self._request(f"/profiles/{tge_environment_id}/status")

    def sync_profile_status(self, tge_environment_id: str) -> dict[str, Any]:
        return self.get_profile_status(tge_environment_id)

    def start_profile(self, tge_environment_id: str) -> dict[str, Any]:
        return {"status": "SUCCESS", "runtime_status": "STARTING", "message": "Start profile scaffold.", "environment_id": tge_environment_id}

    def attach_profile(self, tge_environment_id: str) -> dict[str, Any]:
        return {"status": "SUCCESS", "runtime_status": "RUNNING", "message": "Attach profile scaffold.", "environment_id": tge_environment_id}

    def stop_profile(self, tge_environment_id: str) -> dict[str, Any]:
        return {"status": "SUCCESS", "runtime_status": "STOPPED", "message": "Stop profile scaffold.", "environment_id": tge_environment_id}


def update_profile_from_result(profile: TGEProfile, result: dict[str, Any]) -> None:
    status = str(result.get("status", "UNKNOWN_ERROR"))
    profile.connection_status = status
    profile.last_connection_test_at = utc_now()
    profile.last_connection_error = None if status == "SUCCESS" else str(result.get("message", status))
    runtime_status = result.get("runtime_status") or result.get("data", {}).get("runtime_status")
    if runtime_status:
        profile.runtime_status = str(runtime_status)
    if result.get("data", {}).get("websocket_url"):
        profile.websocket_url = result["data"]["websocket_url"]
    if result.get("data", {}).get("debug_port"):
        profile.debug_port = int(result["data"]["debug_port"])
    profile.last_synced_at = utc_now()
