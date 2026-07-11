from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.adapters.base import PlatformAdapter


X_STATUS_RE = re.compile(r"^/(?P<username>[^/]+)/status/(?P<tweet_id>\d+)")


def normalize_x_post_url(url: str) -> dict[str, Any]:
    parsed = urlparse((url or "").strip())
    host = parsed.netloc.lower().replace("www.", "")
    if host not in {"x.com", "twitter.com"}:
        return {"valid": False, "reason": "unsupported X host", "url": url}
    match = X_STATUS_RE.match(parsed.path)
    if not match:
        return {"valid": False, "reason": "unsupported X status URL", "url": url}
    username = match.group("username")
    tweet_id = match.group("tweet_id")
    canonical_url = f"https://x.com/{username}/status/{tweet_id}"
    return {
        "valid": True,
        "platform": "x",
        "author_handle": username,
        "external_post_id": tweet_id,
        "source_post_id": tweet_id,
        "canonical_url": canonical_url,
        "url": canonical_url,
    }


class XAdapter(PlatformAdapter):
    platform = "x"
    adapter_name = "XAdapter"
    version = "v1"
    capabilities = {
        "BROWSE",
        "OPEN_POST",
        "REPLY",
        "REPLY_FILL",
        "MANUAL_CONFIRM",
        "SUBMISSION_SCAFFOLD",
        "LIKE",
        "PROFILE_VISIT",
    }

    def normalize_url(self, url: str) -> dict[str, Any]:
        return normalize_x_post_url(url)

    def _locator(self, page: Any, selector):
        selector_type = (selector.selector_type or "css").lower()
        if selector_type == "xpath":
            return page.locator(f"xpath={selector.selector_value}")
        if selector_type == "text":
            return page.get_by_text(selector.selector_value)
        return page.locator(selector.selector_value)

    def _selector_locator(self, page: Any, key: str, action_type: str | None = None):
        selector = self.selector(key, action_type=action_type)
        if not selector:
            return None, None
        return selector, self._locator(page, selector).first

    def open_post(self, page: Any, url: str) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario in {"page_load_failed", "browser_disconnected", "worker_offline"}:
            code = {
                "page_load_failed": "X_PAGE_LOAD_FAILED",
                "browser_disconnected": "BROWSER_DISCONNECTED",
                "worker_offline": "WORKER_OFFLINE",
            }[scenario]
            return {"opened": False, "code": code, "reason": f"test mode {scenario}"}
        normalized = self.normalize_url(url)
        if not normalized.get("valid"):
            return {"opened": False, "code": "X_PAGE_LOAD_FAILED", **normalized}
        if self.mock_mode:
            return {
                "opened": True,
                "status": "OPENED",
                "current_url": normalized["canonical_url"],
                "canonical_url": normalized["canonical_url"],
                "external_post_id": normalized["external_post_id"],
                "page_title": "Mock X Post",
                "mock": True,
            }
        try:
            page.goto(normalized["canonical_url"], wait_until="domcontentloaded", timeout=15000)
            return {
                "opened": True,
                "status": "OPENED",
                "current_url": getattr(page, "url", normalized["canonical_url"]),
                "canonical_url": normalized["canonical_url"],
                "external_post_id": normalized["external_post_id"],
                "page_title": page.title(),
            }
        except Exception as exc:
            return {"opened": False, "code": "X_PAGE_LOAD_FAILED", "reason": str(exc), **normalized}

    def detect_login_required(self, page: Any) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario == "login_required":
            return {"detected": True, "test_mode": True}
        if self.mock_mode:
            return {"detected": False, "mock": True}
        return self._detect_state(page, "login_required_indicator")

    def detect_rate_limit(self, page: Any) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario == "rate_limited":
            return {"detected": True, "test_mode": True}
        if self.mock_mode:
            return {"detected": False, "mock": True}
        return self._detect_state(page, "rate_limit_indicator")

    def detect_error_state(self, page: Any) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario == "error_state":
            return {"detected": True, "test_mode": True}
        if self.mock_mode:
            return {"detected": False, "mock": True}
        return self._detect_state(page, "error_indicator")

    def capture_state(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"status": "CAPTURED", "mock": True, "current_url": "https://x.com/mock/status/1"}
        return {
            "status": "CAPTURED",
            "current_url": getattr(page, "url", None),
            "title": page.title() if page else None,
        }

    def find_reply_box(self, page: Any) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario == "reply_box_not_found":
            return {"found": False, "code": "X_REPLY_BOX_NOT_FOUND", "reason": "test mode reply box not found"}
        if scenario == "editor_not_ready":
            return {"found": False, "code": "X_EDITOR_NOT_READY", "reason": "test mode editor not ready"}
        if self.mock_mode:
            return {"found": True, "status": "REPLY_BOX_FOUND", "mock": True}
        login = self.detect_login_required(page)
        if login.get("detected"):
            return {"found": False, "code": "X_LOGIN_REQUIRED", "reason": "X login required"}
        limited = self.detect_rate_limit(page)
        if limited.get("detected"):
            return {"found": False, "code": "X_RATE_LIMITED", "reason": "X rate limited"}
        error = self.detect_error_state(page)
        if error.get("detected"):
            return {"found": False, "code": "X_UNKNOWN_ERROR", "reason": "X error indicator detected"}

        reply_selectors = self.selectors("reply_button", "PREPARE_REPLY")
        reply_selector = None
        last_error = None
        for candidate in reply_selectors:
            reply_button = self._locator(page, candidate).first
            try:
                reply_button.wait_for(state="visible", timeout=5000)
                reply_button.click(timeout=3000)
                reply_selector = candidate
                break
            except Exception as exc:
                last_error = str(exc)
        if reply_selectors and not reply_selector:
            return {"found": False, "code": "X_REPLY_BOX_NOT_FOUND", "reason": last_error}

        editor_selectors = self.selectors("reply_textarea_or_editor", action_type="PREPARE_REPLY") or self.selectors(
            "reply_box", action_type="PREPARE_REPLY"
        )
        if not editor_selectors:
            return {"found": False, "code": "X_REPLY_BOX_NOT_FOUND", "reason": "X reply editor selector missing"}
        last_error = None
        for editor_selector in editor_selectors:
            try:
                locator = self._locator(page, editor_selector).first
                locator.wait_for(state="visible", timeout=7000)
                return {
                    "found": True,
                    "status": "REPLY_BOX_FOUND",
                    "locator": locator,
                    "selector_id": editor_selector.id,
                    "selector_version": editor_selector.version,
                    "reply_button_selector_id": reply_selector.id if reply_selector else None,
                }
            except Exception as exc:
                last_error = str(exc)
        return {"found": False, "code": "X_EDITOR_NOT_READY", "reason": last_error}

    def focus_reply_box(self, page: Any, reply_box: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"focused": True, "mock": True}
        reply_box.focus()
        return {"focused": True}

    def fill_reply_box(self, page: Any, reply_box: Any, text: str) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario in {"editor_not_ready", "content_rejected"}:
            return {"filled": False, "code": "X_EDITOR_NOT_READY" if scenario == "editor_not_ready" else "X_CONTENT_REJECTED"}
        if self.mock_mode:
            return {"filled": True, "text_length": len(text), "visible": True, "mock": True}
        try:
            reply_box.evaluate(
                """(node, value) => {
                    node.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, value);
                }""",
                text,
            )
        except Exception:
            reply_box.fill(text)
        visible = False
        try:
            visible = page.get_by_text(text[:80]).first.is_visible(timeout=1500)
        except Exception:
            try:
                visible = text[:40] in (reply_box.inner_text(timeout=1500) or "")
            except Exception:
                visible = False
        return {"filled": bool(visible), "text_length": len(text), "visible": visible}

    def fill_reply(self, page: Any, text: str) -> dict[str, Any]:
        reply_box = self.find_reply_box(page)
        if not reply_box.get("found"):
            return {
                "filled": False,
                "code": reply_box.get("code", "X_REPLY_BOX_NOT_FOUND"),
                "reason": reply_box.get("reason", "reply box not found"),
            }
        self.focus_reply_box(page, reply_box)
        filled = self.fill_reply_box(page, reply_box, text)
        if not filled.get("filled"):
            return {"filled": False, "code": "X_EDITOR_NOT_READY", **filled}
        return {"filled": True, "status": "WAITING_MANUAL", **filled}

    def detect_submit_button(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"detected": True, "code": "SUBMISSION_SCAFFOLD", "mock": True}
        selector, locator = self._selector_locator(page, "submit_button_scaffold", "SUBMIT_REPLY")
        if not locator:
            return {"detected": False, "code": "NOT_IMPLEMENTED", "reason": "X submit selector scaffold missing"}
        try:
            return {"detected": locator.is_visible(timeout=1000), "selector_id": selector.id}
        except Exception as exc:
            return {"detected": False, "code": "X_UNKNOWN_ERROR", "reason": str(exc)}

    def submit_reply(self, page: Any, *, allow_auto_submit: bool = False) -> dict[str, Any]:
        return {
            "submitted": False,
            "code": "MANUAL_REQUIRED" if not allow_auto_submit else "NOT_IMPLEMENTED",
            "reason": "X auto submit is not enabled in v1; use manual confirm.",
            "mock": self.mock_mode,
        }

    def verify_reply_success(self, page: Any, reply_content: str | None = None) -> dict[str, Any]:
        if self.test_scenario(page) == "failed":
            return {"verified": False, "success": False, "reason": "test mode verification failed"}
        if self.mock_mode:
            return {"verified": True, "success": True, "mock": True}
        if reply_content:
            try:
                visible = page.get_by_text(reply_content[:80]).first.is_visible(timeout=5000)
                return {"verified": bool(visible), "success": bool(visible)}
            except Exception:
                pass
        return {"verified": False, "success": False, "reason": "manual confirmation accepted without page verification"}

    def get_submitted_reply_url(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"url": "https://x.com/mock/status/1", "mock": True}
        return {"url": getattr(page, "url", None)}

    def get_submitted_reply_id(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"external_id": "x-mock-reply", "mock": True}
        return {"external_id": None, "code": "UNKNOWN"}
