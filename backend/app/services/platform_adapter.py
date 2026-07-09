from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSelector


class PlatformAdapter:
    def __init__(self, platform: str, db: Session, mock_mode: bool = True):
        self.platform = platform
        self.db = db
        self.mock_mode = mock_mode

    def selector(self, key: str) -> PlatformSelector | None:
        return self.db.scalar(
            select(PlatformSelector)
            .where(
                PlatformSelector.platform == self.platform,
                PlatformSelector.selector_key == key,
                PlatformSelector.enabled.is_(True),
            )
            .order_by(PlatformSelector.id.asc())
        )

    def _locator(self, page: Any, selector: PlatformSelector):
        selector_type = (selector.selector_type or "css").lower()
        if selector_type == "xpath":
            return page.locator(f"xpath={selector.selector_value}")
        if selector_type == "text":
            return page.get_by_text(selector.selector_value)
        return page.locator(selector.selector_value)

    def find_reply_box(self, page: Any):
        if self.mock_mode:
            return {"found": True, "mock": True}
        selector = self.selector("reply_box")
        if not selector:
            return {"found": False, "reason": "reply_box selector missing"}
        locator = self._locator(page, selector).first
        try:
            locator.wait_for(state="visible", timeout=5000)
        except Exception as exc:
            return {"found": False, "reason": str(exc)}
        return {"found": True, "locator": locator, "selector_id": selector.id}

    def focus_reply_box(self, page: Any, reply_box: Any):
        if self.mock_mode:
            return {"focused": True, "mock": True}
        reply_box.focus()
        return {"focused": True}

    def fill_reply_box(self, page: Any, reply_box: Any, text: str):
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

    def detect_submitted(self, page: Any):
        if self.mock_mode:
            return {"submitted": True, "mock": True}
        return {"submitted": False, "reason": "manual confirmation accepted"}

    def detect_comment_disabled(self, page: Any):
        return self._detect_state(page, "comment_disabled")

    def detect_login_required(self, page: Any):
        return self._detect_state(page, "login_required")

    def detect_rate_limited(self, page: Any):
        return self._detect_state(page, "rate_limited")

    def _detect_state(self, page: Any, selector_key: str):
        if self.mock_mode:
            return {"detected": False, "mock": True}
        selector = self.selector(selector_key)
        if not selector:
            return {"detected": False, "reason": "selector missing"}
        try:
            return {"detected": self._locator(page, selector).first.is_visible(timeout=1000)}
        except Exception:
            return {"detected": False}

    def browse_post(self, page: Any, url: str):
        if self.mock_mode:
            return {"browsed": True, "url": url, "mock": True}
        page.goto(url)
        return {"browsed": True, "url": url}

    def like_post(self, page: Any):
        if self.mock_mode:
            return {"liked": True, "mock": True}
        selector = self.selector("like_button")
        if not selector:
            return {"liked": False, "reason": "like_button selector missing"}
        self._locator(page, selector).first.click()
        return {"liked": True}

    def bookmark_post(self, page: Any):
        if self.mock_mode:
            return {"bookmarked": True, "mock": True}
        selector = self.selector("bookmark_button")
        if not selector:
            return {"bookmarked": False, "reason": "bookmark_button selector missing"}
        self._locator(page, selector).first.click()
        return {"bookmarked": True}

    def visit_profile(self, page: Any, profile_url: str):
        if self.mock_mode:
            return {"visited": True, "profile_url": profile_url, "mock": True}
        page.goto(profile_url)
        return {"visited": True, "profile_url": profile_url}

    def scroll_randomly(self, page: Any):
        if self.mock_mode:
            return {"scrolled": True, "mock": True}
        page.mouse.wheel(0, 600)
        return {"scrolled": True}

    def pause_randomly(self, min_seconds: int, max_seconds: int):
        return {"paused": True, "min_seconds": min_seconds, "max_seconds": max_seconds, "mock": self.mock_mode}

    def open_related_post(self, page: Any):
        return {"opened": False, "reason": "related post navigation is adapter-specific"}

    def detect_like_available(self, page: Any):
        return self._detect_state(page, "like_button")

    def detect_profile_available(self, page: Any):
        return self._detect_state(page, "profile_link")
