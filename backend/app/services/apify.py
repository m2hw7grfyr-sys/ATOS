from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CrawlLog, DataSource, Platform, Post, utc_now


class ApifyServiceError(RuntimeError):
    pass


@dataclass
class NormalizedPost:
    title: str
    content: str
    url: str
    author: Optional[str]
    community: Optional[str]
    source_post_id: Optional[str]
    published_at: Optional[datetime]
    raw_json: dict[str, Any]

    @property
    def url_hash(self) -> Optional[str]:
        if not self.url:
            return None
        return hashlib.sha256(self.url.strip().encode("utf-8")).hexdigest()


def _value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        current: Any = item
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current not in (None, ""):
            return current
    return None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def normalize_post(item: dict[str, Any]) -> NormalizedPost:
    return NormalizedPost(
        title=_text(_value(item, "title", "name", "headline", "text")),
        content=_text(
            _value(
                item,
                "content",
                "body",
                "selftext",
                "text",
                "description",
                "caption",
            )
        ),
        url=_text(
            _value(item, "url", "postUrl", "permalink", "link", "canonicalUrl")
        ),
        author=_text(
            _value(
                item,
                "author",
                "username",
                "userName",
                "user.username",
                "ownerUsername",
            )
        )
        or None,
        community=_text(
            _value(
                item,
                "community",
                "subreddit",
                "groupName",
                "channelName",
                "board",
            )
        )
        or None,
        source_post_id=_text(
            _value(
                item,
                "source_post_id",
                "id",
                "postId",
                "tweetId",
                "shortCode",
                "facebookId",
            )
        )
        or None,
        published_at=_datetime(
            _value(
                item,
                "published_at",
                "publishedAt",
                "createdAt",
                "created_utc",
                "timestamp",
                "date",
            )
        ),
        raw_json=item,
    )


class ApifyService:
    def __init__(
        self,
        db: Session,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.db = db
        self.opener = opener
        self.settings = get_settings()

    def _config(self, source: DataSource) -> dict[str, Any]:
        return dict(source.config or {})

    def _token(self, source: DataSource) -> str:
        return str(self._config(source).get("apify_token") or self.settings.apify_token)

    def _actor_id(self, source: DataSource) -> str:
        actor_id = str(self._config(source).get("actor_id") or "").strip()
        if not actor_id:
            raise ApifyServiceError("Actor ID is required")
        return actor_id.replace("/", "~")

    def _request(
        self,
        method: str,
        path: str,
        token: str,
        payload: Optional[dict[str, Any]] = None,
        query: Optional[dict[str, Any]] = None,
        timeout: int = 150,
    ) -> Any:
        url = f"{self.settings.apify_api_base_url.rstrip('/')}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with self.opener(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ApifyServiceError(f"Apify HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApifyServiceError(f"Apify request failed: {exc}") from exc

    def test_connection(self, source: DataSource) -> dict[str, Any]:
        token = self._token(source)
        if not token:
            raise ApifyServiceError("APIFY_TOKEN is not configured")
        actor_id = self._actor_id(source)
        response = self._request("GET", f"acts/{quote(actor_id, safe='')}", token)
        actor = response.get("data", response)
        return {
            "connected": True,
            "actor_id": actor_id,
            "actor_name": actor.get("name") or self._config(source).get("actor_name"),
        }

    def run(self, source: DataSource) -> CrawlLog:
        config = self._config(source)
        platform = self.db.get(Platform, source.platform_id)
        platform_slug = platform.slug if platform else str(config.get("platform") or "unknown")
        actor_id = str(config.get("actor_id") or "")
        log = CrawlLog(
            data_source_id=source.id,
            platform=platform_slug,
            actor_id=actor_id,
            status="RUNNING",
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        try:
            if not source.enabled:
                raise ApifyServiceError("Data source is disabled")
            token = self._token(source)
            if not token:
                raise ApifyServiceError("APIFY_TOKEN is not configured")
            normalized_actor_id = self._actor_id(source)
            actor_input = config.get("input_json") or {}
            if not isinstance(actor_input, dict):
                raise ApifyServiceError("Input JSON must be an object")
            max_items = max(1, min(int(config.get("max_items") or 100), 1000))

            run_response = self._request(
                "POST",
                f"acts/{quote(normalized_actor_id, safe='')}/runs",
                token,
                payload=actor_input,
                query={"waitForFinish": 120},
            )
            run_data = run_response.get("data", run_response)
            run_status = str(run_data.get("status") or "")
            if run_status not in {"SUCCEEDED"}:
                raise ApifyServiceError(
                    f"Actor run did not succeed (status: {run_status or 'unknown'})"
                )
            dataset_id = run_data.get("defaultDatasetId")
            if not dataset_id:
                raise ApifyServiceError("Actor run returned no default dataset")

            items = self._request(
                "GET",
                f"datasets/{quote(str(dataset_id), safe='')}/items",
                token,
                query={"clean": "true", "format": "json", "limit": max_items},
            )
            if not isinstance(items, list):
                raise ApifyServiceError("Dataset items response is not a JSON array")
            log.raw_response_excerpt = json.dumps(
                items[:3], ensure_ascii=False, default=str
            )[:2000]
            self._store_items(source, platform, items, log)
            log.status = "SUCCEEDED"
            source.status = "ACTIVE"
            source.last_run_at = utc_now()
            config["last_error"] = ""
        except Exception as exc:
            message = str(exc)
            log.status = "FAILED"
            log.error_count = max(log.error_count, 1)
            log.error_message = message[:2000]
            source.status = "ERROR"
            config["last_error"] = message[:500]
        finally:
            source.config = config
            log.finished_at = utc_now()
            self.db.commit()
            self.db.refresh(log)
        return log

    def _store_items(
        self,
        source: DataSource,
        platform: Optional[Platform],
        items: list[Any],
        log: CrawlLog,
    ) -> None:
        if platform is None:
            raise ApifyServiceError("Data source platform does not exist")
        log.total_items = len(items)
        for item in items:
            if not isinstance(item, dict):
                log.error_count += 1
                continue
            normalized = normalize_post(item)
            duplicate_filters = []
            if normalized.source_post_id:
                duplicate_filters.append(
                    Post.source_post_id == normalized.source_post_id
                )
            elif normalized.url_hash:
                duplicate_filters.append(Post.url_hash == normalized.url_hash)
            if duplicate_filters:
                duplicate = self.db.scalar(
                    select(Post.id).where(
                        Post.platform_id == platform.id,
                        or_(*duplicate_filters),
                    )
                )
                if duplicate:
                    log.duplicate_count += 1
                    continue
            self.db.add(
                Post(
                    platform_id=platform.id,
                    data_source_id=source.id,
                    source_post_id=normalized.source_post_id,
                    url_hash=normalized.url_hash,
                    community=normalized.community,
                    author=normalized.author,
                    title=normalized.title,
                    content=normalized.content,
                    url=normalized.url,
                    published_at=normalized.published_at,
                    raw_json=normalized.raw_json,
                    status="NEW",
                )
            )
            log.inserted_count += 1
