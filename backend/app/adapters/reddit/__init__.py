from __future__ import annotations

from typing import Any

from app.adapters.base import PlatformAdapter


class RedditAdapter(PlatformAdapter):
    platform = "reddit"
    adapter_name = "RedditAdapter"
    version = "v1"
    capabilities = {"REPLY", "BROWSE", "LIKE", "PROFILE_VISIT"}

    def _locator(self, page: Any, selector):
        selector_type = (selector.selector_type or "css").lower()
        if selector_type == "xpath":
            return page.locator(f"xpath={selector.selector_value}")
        if selector_type == "text":
            return page.get_by_text(selector.selector_value)
        return page.locator(selector.selector_value)

    def find_reply_box(self, page: Any) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario == "reply_box_not_found":
            return {"found": False, "code": "REPLY_BOX_NOT_FOUND", "reason": "test mode reply box not found"}
        if self.mock_mode:
            return {"found": True, "mock": True}
        selectors = self.selectors("reply_box", action_type="PREPARE_REPLY")
        if not selectors:
            return {"found": False, "reason": "reply_box selector missing"}
        last_error = None
        for selector in selectors:
            locator = self._locator(page, selector).first
            try:
                locator.wait_for(state="visible", timeout=5000)
                return {"found": True, "locator": locator, "selector_id": selector.id, "selector_version": selector.version}
            except Exception as exc:
                last_error = str(exc)
        return {"found": False, "code": "REPLY_BOX_NOT_FOUND", "reason": last_error or "reply box not found"}

    def focus_reply_box(self, page: Any, reply_box: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"focused": True, "mock": True}
        reply_box.focus()
        return {"focused": True}

    def fill_reply_box(self, page: Any, reply_box: Any, text: str) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario in {"editor_not_ready", "content_rejected"}:
            return {"filled": False, "code": "EDITOR_NOT_READY" if scenario == "editor_not_ready" else "CONTENT_REJECTED"}
        if self.mock_mode:
            return {"filled": True, "text_length": len(text), "mock": True}
        reply_box.evaluate(
            """(node, value) => {
                node.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, value);
            }""",
            text,
        )
        return {"filled": True, "text_length": len(text)}

    def fill_reply(self, page: Any, text: str) -> dict[str, Any]:
        scenario = self.test_scenario(page)
        if scenario in {"editor_not_ready", "content_rejected"}:
            return {"filled": False, "code": "EDITOR_NOT_READY" if scenario == "editor_not_ready" else "CONTENT_REJECTED"}
        reply_box = self.find_reply_box(page)
        if not reply_box.get("found"):
            return {"filled": False, "reason": reply_box.get("reason", "reply box not found")}
        self.focus_reply_box(page, reply_box)
        return self.fill_reply_box(page, reply_box, text)

    def detect_submit_button(self, page: Any) -> dict[str, Any]:
        if self.test_scenario(page) == "submission_failed":
            return {"detected": False, "code": "SUBMISSION_FAILED", "reason": "test mode submission failed"}
        if self.mock_mode:
            return {"detected": True, "mock": True}
        selectors = self.selectors("comment_button", action_type="SUBMIT_REPLY") or self.selectors(
            "comment_button", action_type="PREPARE_REPLY"
        )
        if not selectors:
            return {"detected": False, "code": "SUBMIT_BUTTON_NOT_FOUND", "reason": "comment_button selector missing"}
        last_error = None
        for selector in selectors:
            try:
                locator = self._locator(page, selector).first
                visible = locator.is_visible(timeout=1500)
                if visible:
                    return {"detected": True, "selector_id": selector.id}
            except Exception as exc:
                last_error = str(exc)
        return {"detected": False, "code": "SUBMIT_BUTTON_NOT_FOUND", "reason": last_error}

    def submit_reply(self, page: Any, *, allow_auto_submit: bool = False) -> dict[str, Any]:
        if not allow_auto_submit:
            return {"submitted": False, "code": "MANUAL_REQUIRED", "reason": "automatic submission is disabled by policy"}
        if self.mock_mode:
            return {"submitted": True, "mock": True}
        for detector, code in [
            (self.detect_login_required, "LOGIN_REQUIRED"),
            (self.detect_rate_limit, "RATE_LIMITED"),
            (self.detect_comment_disabled, "COMMENT_DISABLED"),
        ]:
            result = detector(page)
            if result.get("detected"):
                return {
                    "submitted": False,
                    "code": "BLOCKED_OR_MANUAL_REQUIRED",
                    "failure_type": code,
                    "reason": result.get("reason") or code,
                }
        button = self.detect_submit_button(page)
        if not button.get("detected"):
            return {"submitted": False, "code": "SUBMIT_BUTTON_NOT_FOUND", "reason": button.get("reason")}
        selector = self.selector("comment_button", action_type="SUBMIT_REPLY") or self.selector(
            "comment_button", action_type="PREPARE_REPLY"
        )
        try:
            self._locator(page, selector).first.click(timeout=3000)
        except Exception as exc:
            return {"submitted": False, "code": "PLATFORM_ERROR", "reason": str(exc)}
        return {"submitted": True, "code": "SUBMITTED"}

    def verify_reply_success(self, page: Any, reply_content: str | None = None) -> dict[str, Any]:
        if self.test_scenario(page) == "failed":
            return {"verified": False, "success": False, "reason": "test mode verification failed"}
        if self.mock_mode:
            return {"verified": True, "success": True, "mock": True}
        if reply_content:
            try:
                visible = page.get_by_text(reply_content[:80]).first.is_visible(timeout=5000)
                if visible:
                    return {"verified": True, "success": True}
            except Exception:
                pass
        detected = self.detect_reply_success(page)
        return {"verified": bool(detected.get("success")), **detected}

    def get_submitted_reply_url(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"url": "https://www.reddit.com/comments/mock/submission", "mock": True}
        return {"url": getattr(page, "url", None)}

    def get_submitted_reply_id(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"external_id": "reddit-mock-comment", "mock": True}
        return {"external_id": None, "code": "UNKNOWN"}
