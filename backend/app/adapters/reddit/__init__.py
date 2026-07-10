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
        if self.mock_mode:
            return {"found": True, "mock": True}
        selector = self.selector("reply_box", action_type="PREPARE_REPLY")
        if not selector:
            return {"found": False, "reason": "reply_box selector missing"}
        locator = self._locator(page, selector).first
        try:
            locator.wait_for(state="visible", timeout=5000)
        except Exception as exc:
            return {"found": False, "reason": str(exc)}
        return {"found": True, "locator": locator, "selector_id": selector.id}

    def focus_reply_box(self, page: Any, reply_box: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"focused": True, "mock": True}
        reply_box.focus()
        return {"focused": True}

    def fill_reply_box(self, page: Any, reply_box: Any, text: str) -> dict[str, Any]:
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
        reply_box = self.find_reply_box(page)
        if not reply_box.get("found"):
            return {"filled": False, "reason": reply_box.get("reason", "reply box not found")}
        self.focus_reply_box(page, reply_box)
        return self.fill_reply_box(page, reply_box, text)
