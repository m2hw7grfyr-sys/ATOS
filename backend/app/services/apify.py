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
from app.models import ActorMapping, CrawlLog, DataSource, Platform, Post, utc_now


class ApifyServiceError(RuntimeError):
    pass


@dataclass
class NormalizedPost:
    title: str
    content: str
    url: str
    author: Optional[str]
    author_id: Optional[str]
    community: Optional[str]
    source_post_id: Optional[str]
    published_at: Optional[datetime]
    score: int
    comment_count: int
    media: list[Any]
    language: str
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
        author_id=_text(_value(item, "author_id", "authorId", "user.id", "author.id")) or None,
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
        score=int(_value(item, "score", "upvotes", "likes", "points") or 0),
        comment_count=int(_value(item, "comment_count", "commentCount", "commentsCount", "numComments") or 0),
        media=_value(item, "media", "images", "attachments") or [],
        language=_text(_value(item, "language", "lang")) or "en",
        raw_json=item,
    )


def normalize_post_with_mapping(item: dict[str, Any], mapping: ActorMapping) -> tuple[NormalizedPost, list[str]]:
    warnings = []

    def get(path: str | None) -> Any:
        return _value(item, path) if path else None

    title = _text(get(mapping.title_path))
    content = _text(get(mapping.content_path))
    url = _text(get(mapping.url_path))
    source_post_id = _text(get(mapping.source_post_id_path)) or None
    if not title:
        warnings.append("title missing")
    if not url:
        warnings.append("url missing")
    if not source_post_id:
        warnings.append("source_post_id missing")
    media_value = get(mapping.media_path) or []
    if not isinstance(media_value, list):
        media_value = [media_value]
    return (
        NormalizedPost(
            title=title,
            content=content,
            url=url,
            author=_text(get(mapping.author_path)) or None,
            author_id=_text(get(mapping.author_id_path)) or None,
            community=_text(get(mapping.community_path)) or None,
            source_post_id=source_post_id,
            published_at=_datetime(get(mapping.published_at_path)),
            score=int(get(mapping.score_path) or 0),
            comment_count=int(get(mapping.comment_count_path) or 0),
            media=media_value,
            language=_text(get(mapping.language_path)) or "en",
            raw_json=item,
        ),
        warnings,
    )


def mapping_preview(mapping_values: dict[str, Any], raw_item: dict[str, Any]) -> dict[str, Any]:
    mapping = ActorMapping(
        actor_id=str(mapping_values.get("actor_id") or "preview"),
        platform=str(mapping_values.get("platform") or "preview"),
        mapping_name=str(mapping_values.get("mapping_name") or "Preview"),
        **{
            key: mapping_values.get(key)
            for key in [
                "title_path",
                "content_path",
                "url_path",
                "author_path",
                "author_id_path",
                "community_path",
                "source_post_id_path",
                "published_at_path",
                "score_path",
                "comment_count_path",
                "media_path",
                "language_path",
            ]
        },
    )
    normalized, warnings = normalize_post_with_mapping(raw_item, mapping)
    return {
        "normalized_post_preview": {
            "title": normalized.title,
            "content": normalized.content,
            "url": normalized.url,
            "author": normalized.author,
            "author_id": normalized.author_id,
            "community": normalized.community,
            "source_post_id": normalized.source_post_id,
            "published_at": normalized.published_at.isoformat() if normalized.published_at else None,
            "score": normalized.score,
            "comment_count": normalized.comment_count,
            "media": normalized.media,
            "language": normalized.language,
        },
        "missing_fields": [item.replace(" missing", "") for item in warnings],
        "warnings": warnings,
    }


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
        config = self._config(source)
        actor_id = str(config.get("actor_id") or "")
        mapping = self.db.scalar(
            select(ActorMapping)
            .where(
                ActorMapping.enabled.is_(True),
                ActorMapping.platform == platform.slug,
                or_(ActorMapping.data_source_id == source.id, ActorMapping.actor_id == actor_id),
            )
            .order_by(ActorMapping.data_source_id.desc(), ActorMapping.id.asc())
        )
        if mapping:
            log.mapping_id = mapping.id
        else:
            log.mapping_missing = True
        log.total_items = len(items)
        for item in items:
            if not isinstance(item, dict):
                log.error_count += 1
                continue
            if mapping:
                normalized, warnings = normalize_post_with_mapping(item, mapping)
            else:
                normalized = normalize_post(item)
                warnings = ["mapping missing"]
            log.normalization_warning_count += len(warnings)
            raw_json_hash = hashlib.sha256(
                json.dumps(item, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
            final_url_hash = normalized.url_hash or raw_json_hash
            duplicate_filters = []
            if normalized.source_post_id:
                duplicate_filters.append(
                    Post.source_post_id == normalized.source_post_id
                )
            duplicate_filters.append(Post.url_hash == final_url_hash)
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
                    mapping_id=mapping.id if mapping else None,
                    source_post_id=normalized.source_post_id,
                    url_hash=final_url_hash,
                    community=normalized.community,
                    author=normalized.author,
                    author_id=normalized.author_id,
                    title=normalized.title or "(untitled)",
                    content=normalized.content,
                    url=normalized.url,
                    language=normalized.language,
                    score=normalized.score,
                    comment_count=normalized.comment_count,
                    media=normalized.media,
                    published_at=normalized.published_at,
                    raw_json=normalized.raw_json,
                    status="INCOMPLETE" if (not normalized.url or not normalized.title) else "NORMALIZED",
                )
            )
            if not normalized.url or not normalized.title:
                log.incomplete_count += 1
            log.inserted_count += 1
