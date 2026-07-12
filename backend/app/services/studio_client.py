from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.models import Platform, Post


class StudioClientError(Exception):
    user_message = "送入Studio失败"


class StudioUnavailableError(StudioClientError):
    user_message = "Studio服务不可达，请检查Studio是否启动"


class StudioAuthError(StudioClientError):
    user_message = "Studio鉴权失败，请检查内部Token配置"


class StudioValidationError(StudioClientError):
    user_message = "Studio请求校验失败"


class StudioNotFoundError(StudioClientError):
    user_message = "Studio接口不存在"


class StudioClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.studio_base_url.rstrip("/")
        self.token = settings.studio_push_api_token
        self.timeout = settings.studio_request_timeout_seconds

    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token and self.token != "replace-with-a-strong-token":
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, *, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.base_url:
            raise StudioUnavailableError("Studio base URL is not configured")
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.request(method, path, headers=self.headers(), json=json, params=params)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise StudioUnavailableError("Studio service is unreachable") from exc
        except httpx.HTTPError as exc:
            raise StudioUnavailableError("Studio request failed") from exc

        if response.status_code == 401:
            raise StudioAuthError("Studio authentication failed")
        if response.status_code == 404:
            raise StudioNotFoundError("Studio endpoint not found")
        if response.status_code == 422:
            raise StudioValidationError("Studio payload validation failed")
        if response.status_code >= 400:
            raise StudioClientError(f"Studio returned HTTP {response.status_code}")
        return response.json()

    def health_check(self) -> dict[str, Any]:
        return self.request("GET", "/health")

    def push_content_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/api/content-items/push", json=payload)

    def get_source_status(self, *, source_platform: str, source_post_id: str | None, atos_post_id: str | None) -> dict[str, Any]:
        return self.request(
            "GET",
            "/api/content-items/source-status",
            params={
                "source_platform": source_platform,
                "source_post_id": source_post_id or "",
                "atos_post_id": atos_post_id or "",
            },
        )

    def get_source_status_batch(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self.request("POST", "/api/content-items/source-status/batch", json={"items": items})


def build_studio_push_payload(
    post: Post,
    platform: Platform,
    *,
    requested_content_type: str,
    target_platforms: list[str],
    operator_note: str,
) -> dict[str, Any]:
    return {
        "source_platform": platform.slug,
        "atos_post_id": str(post.id),
        "source_post_id": post.source_post_id,
        "source_url": post.url,
        "title": post.title,
        "body": post.content,
        "author": post.author,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "collected_at": post.created_at.isoformat() if post.created_at else None,
        "source_score": post.score,
        "comment_count": post.comment_count,
        "risk_level": None,
        "tags": post.tags or [],
        "metadata": {
            "atos_post_uuid": post.uuid,
            "community": post.community,
            "language": post.language,
            "status": post.status,
            "pipeline_stage": post.pipeline_stage,
        },
        "push_context": {
            "requested_content_type": requested_content_type,
            "target_platforms": target_platforms,
            "operator_note": operator_note,
        },
    }


def studio_error_summary(exc: Exception) -> str:
    if isinstance(exc, StudioClientError):
        return exc.user_message
    return "送入Studio失败"
