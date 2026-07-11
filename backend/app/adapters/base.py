from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSelector


class PlatformAdapter(ABC):
    platform = "generic"
    adapter_name = "GenericAdapter"
    version = "v1"
    capabilities: set[str] = set()

    def __init__(self, db: Session, mock_mode: bool = True):
        self.db = db
        self.mock_mode = mock_mode

    def authenticate(self) -> dict[str, Any]:
        return {"authenticated": True, "mock": self.mock_mode}

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "HEALTHY",
            "adapter": self.adapter_name,
            "platform": self.platform,
            "version": self.version,
            "capabilities": sorted(self.capabilities),
        }

    def selector(self, key: str, action_type: str | None = None) -> PlatformSelector | None:
        statement = select(PlatformSelector).where(
            PlatformSelector.platform == self.platform,
            PlatformSelector.selector_key == key,
            PlatformSelector.enabled.is_(True),
        )
        if action_type:
            statement = statement.where(
                (PlatformSelector.action_type == action_type) | (PlatformSelector.action_type.is_(None))
            )
        return self.db.scalar(statement.order_by(PlatformSelector.action_type.desc(), PlatformSelector.id.asc()))

    def open_post(self, page: Any, url: str) -> dict[str, Any]:
        if "BROWSE" not in self.capabilities and "REPLY" not in self.capabilities:
            return {"opened": False, "reason": "capability not supported"}
        if self.mock_mode:
            return {"opened": True, "url": url, "mock": True}
        page.goto(url)
        return {"opened": True, "url": url}

    @abstractmethod
    def find_reply_box(self, page: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fill_reply(self, page: Any, text: str) -> dict[str, Any]:
        raise NotImplementedError

    def focus_reply_box(self, page: Any, reply_box: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"focused": True, "mock": True}
        reply_box.focus()
        return {"focused": True}

    def fill_reply_box(self, page: Any, reply_box: Any, text: str) -> dict[str, Any]:
        if self.mock_mode:
            return {"filled": True, "text_length": len(text), "mock": True}
        reply_box.fill(text)
        return {"filled": True, "text_length": len(text)}

    def browse(self, page: Any, url: str) -> dict[str, Any]:
        if "BROWSE" not in self.capabilities:
            return {"browsed": False, "reason": "BROWSE capability not supported"}
        return self.open_post(page, url)

    def browse_post(self, page: Any, url: str) -> dict[str, Any]:
        return self.browse(page, url)

    def like(self, page: Any) -> dict[str, Any]:
        if "LIKE" not in self.capabilities:
            return {"liked": False, "reason": "LIKE capability not supported"}
        return {"liked": True, "mock": self.mock_mode}

    def like_post(self, page: Any) -> dict[str, Any]:
        return self.like(page)

    def bookmark_post(self, page: Any) -> dict[str, Any]:
        if "BOOKMARK" not in self.capabilities:
            return {"bookmarked": False, "reason": "BOOKMARK capability not supported"}
        return {"bookmarked": True, "mock": self.mock_mode}

    def visit_profile(self, page: Any, profile_url: str) -> dict[str, Any]:
        if "PROFILE_VISIT" not in self.capabilities:
            return {"visited": False, "reason": "PROFILE_VISIT capability not supported"}
        if self.mock_mode:
            return {"visited": True, "profile_url": profile_url, "mock": True}
        page.goto(profile_url)
        return {"visited": True, "profile_url": profile_url}

    def scroll_randomly(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"scrolled": True, "mock": True}
        page.mouse.wheel(0, 640)
        return {"scrolled": True}

    def pause_randomly(self, min_seconds: int, max_seconds: int) -> dict[str, Any]:
        return {"paused": True, "min_seconds": min_seconds, "max_seconds": max_seconds, "mock": self.mock_mode}

    def open_related_post(self, page: Any) -> dict[str, Any]:
        return {"opened": False, "reason": "related post navigation is platform-specific"}

    def get_profile(self, profile_url: str) -> dict[str, Any]:
        return {"profile_url": profile_url, "platform": self.platform, "mock": self.mock_mode}

    def get_post(self, url: str) -> dict[str, Any]:
        return {"url": url, "platform": self.platform, "mock": self.mock_mode}

    def close(self) -> dict[str, Any]:
        return {"closed": True, "mock": self.mock_mode}

    def detect_login_required(self, page: Any) -> dict[str, Any]:
        return self._detect_state(page, "login_required")

    def detect_rate_limit(self, page: Any) -> dict[str, Any]:
        return self._detect_state(page, "rate_limited")

    def detect_rate_limited(self, page: Any) -> dict[str, Any]:
        return self.detect_rate_limit(page)

    def detect_comment_disabled(self, page: Any) -> dict[str, Any]:
        return self._detect_state(page, "comment_disabled")

    def detect_like_available(self, page: Any) -> dict[str, Any]:
        return self._detect_state(page, "like_button")

    def detect_profile_available(self, page: Any) -> dict[str, Any]:
        return self._detect_state(page, "profile_link")

    def detect_reply_success(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"success": True, "mock": True}
        return {"success": False, "reason": "manual confirmation accepted"}

    def detect_submitted(self, page: Any) -> dict[str, Any]:
        detected = self.detect_reply_success(page)
        return {"submitted": bool(detected.get("success")), **detected}

    def detect_submit_button(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"detected": True, "mock": True}
        return {"detected": False, "code": "NOT_IMPLEMENTED", "reason": "submit detection is not implemented"}

    def submit_reply(self, page: Any, *, allow_auto_submit: bool = False) -> dict[str, Any]:
        if not allow_auto_submit:
            return {"submitted": False, "code": "MANUAL_REQUIRED", "reason": "automatic submission is disabled by policy"}
        if self.mock_mode:
            return {"submitted": True, "mock": True}
        return {"submitted": False, "code": "NOT_IMPLEMENTED", "reason": "submission is not implemented"}

    def verify_reply_success(self, page: Any, reply_content: str | None = None) -> dict[str, Any]:
        detected = self.detect_reply_success(page)
        return {"verified": bool(detected.get("success")), **detected}

    def get_submitted_reply_url(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"url": f"https://example.com/{self.platform}/mock-submission", "mock": True}
        return {"url": None, "code": "NOT_IMPLEMENTED"}

    def get_submitted_reply_id(self, page: Any) -> dict[str, Any]:
        if self.mock_mode:
            return {"external_id": f"{self.platform}-mock-comment", "mock": True}
        return {"external_id": None, "code": "NOT_IMPLEMENTED"}

    def _detect_state(self, page: Any, selector_key: str) -> dict[str, Any]:
        if self.mock_mode:
            return {"detected": False, "mock": True}
        selector = self.selector(selector_key)
        if not selector:
            return {"detected": False, "reason": "selector missing"}
        try:
            return {"detected": page.locator(selector.selector_value).first.is_visible(timeout=1000)}
        except Exception:
            return {"detected": False}


class ScaffoldAdapter(PlatformAdapter):
    capabilities: set[str] = {"BROWSE"}

    def find_reply_box(self, page: Any) -> dict[str, Any]:
        return {"found": False, "reason": "REPLY capability not implemented"}

    def fill_reply(self, page: Any, text: str) -> dict[str, Any]:
        return {"filled": False, "reason": "REPLY capability not implemented"}
