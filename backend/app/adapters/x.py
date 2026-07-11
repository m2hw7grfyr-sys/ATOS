from __future__ import annotations

from app.adapters.base import ScaffoldAdapter


class XAdapter(ScaffoldAdapter):
    platform = "x"
    adapter_name = "XAdapter"
    version = "v1-scaffold"
    capabilities = {"BROWSE", "LIKE", "PROFILE_VISIT"}

    def detect_submit_button(self, page):
        if self.mock_mode:
            return {"detected": False, "code": "NOT_IMPLEMENTED", "mock": True}
        return {"detected": False, "code": "NOT_IMPLEMENTED", "reason": "X submission adapter is scaffold only"}

    def submit_reply(self, page, *, allow_auto_submit: bool = False):
        return {
            "submitted": False,
            "code": "NOT_IMPLEMENTED" if allow_auto_submit else "MANUAL_REQUIRED",
            "reason": "X submission is scaffold only",
            "mock": self.mock_mode,
        }

    def verify_reply_success(self, page, reply_content: str | None = None):
        return {"verified": False, "code": "NOT_IMPLEMENTED", "mock": self.mock_mode}
