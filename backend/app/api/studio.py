from __future__ import annotations

import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Platform, Post
from app.response import ok
from app.schemas import (
    StudioApiHealthResponse,
    StudioContentItemListResponse,
    StudioContentItemRead,
    StudioPushBatchRequest,
    StudioPushRequest,
)
from app.services.studio_client import (
    StudioAuthError,
    StudioClient,
    StudioClientError,
    StudioUnavailableError,
    build_studio_push_payload,
    studio_error_summary,
)


router = APIRouter(prefix="/api/studio", tags=["studio"])


def require_studio_api_token(authorization: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.atos_studio_auth_enabled:
        if settings.app_env.lower() == "development":
            return
        raise HTTPException(status_code=403, detail="studio api auth cannot be disabled outside development")

    expected = settings.atos_studio_api_token
    if not expected:
        raise HTTPException(status_code=401, detail="studio api token is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing studio api bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid studio api bearer token")


def serialize_content_item(post: Post, platform: Platform) -> StudioContentItemRead:
    metadata = {
        "atos_status": post.status,
        "pipeline_stage": post.pipeline_stage,
        "community": post.community,
        "language": post.language,
        "data_source_id": post.data_source_id,
    }
    return StudioContentItemRead(
        atos_post_id=str(post.id),
        atos_post_uuid=post.uuid,
        source_platform=platform.slug,
        source_post_id=post.source_post_id,
        source_url=post.url,
        title=post.title,
        body=post.content,
        author=post.author,
        published_at=post.published_at,
        collected_at=post.created_at,
        score=post.score,
        comment_count=post.comment_count,
        risk_level=None,
        tags=post.tags or [],
        metadata=metadata,
    )


def content_query():
    return select(Post, Platform).join(Platform, Platform.id == Post.platform_id)


@router.get("/health")
def studio_api_health(
    request: Request,
    _: None = Depends(require_studio_api_token),
):
    return ok(StudioApiHealthResponse().model_dump(), request.state.trace_id)


@router.get("/content-items")
def list_content_items(
    request: Request,
    platform: Optional[str] = Query(default=None),
    min_score: Optional[int] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    created_after: Optional[datetime] = Query(default=None),
    created_before: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(require_studio_api_token),
):
    statement = content_query()
    if platform:
        statement = statement.where(Platform.slug == platform.lower())
    if min_score is not None:
        statement = statement.where(Post.score >= min_score)
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern),
                Post.author.ilike(pattern),
                Post.community.ilike(pattern),
            )
        )
    if created_after:
        statement = statement.where(Post.created_at >= created_after)
    if created_before:
        statement = statement.where(Post.created_at <= created_before)

    if risk_level is not None and risk_level.lower() not in {"unknown", "none", "null"}:
        return ok(
            StudioContentItemListResponse(items=[], total=0, limit=limit, offset=offset).model_dump(),
            request.state.trace_id,
            "risk_level is not available in current ATOS post schema",
        )

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(statement.order_by(Post.created_at.desc()).offset(offset).limit(limit)).all()
    items = [serialize_content_item(post, item_platform) for post, item_platform in rows]
    payload = StudioContentItemListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
    return ok(payload.model_dump(mode="json"), request.state.trace_id)


@router.get("/content-items/{source_post_id}")
def get_content_item(
    source_post_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_studio_api_token),
):
    conditions = [Post.uuid == source_post_id, Post.source_post_id == source_post_id]
    if source_post_id.isdigit():
        conditions.append(Post.id == int(source_post_id))
    row = db.execute(content_query().where(or_(*conditions)).limit(1)).first()
    if not row:
        raise HTTPException(status_code=404, detail="studio content item not found")
    post, platform = row
    return ok(serialize_content_item(post, platform).model_dump(mode="json"), request.state.trace_id)


def _find_post(db: Session, atos_post_id: str):
    conditions = [Post.uuid == atos_post_id]
    if atos_post_id.isdigit():
        conditions.append(Post.id == int(atos_post_id))
    row = db.execute(content_query().where(or_(*conditions)).limit(1)).first()
    if not row:
        raise HTTPException(status_code=404, detail="ATOS中未找到该帖子")
    return row


def _push_post_to_studio(
    db: Session,
    *,
    atos_post_id: str,
    requested_content_type: str,
    target_platforms: list[str],
    operator_note: str,
) -> dict:
    post, platform = _find_post(db, atos_post_id)
    payload = build_studio_push_payload(
        post,
        platform,
        requested_content_type=requested_content_type,
        target_platforms=target_platforms,
        operator_note=operator_note,
    )
    result = StudioClient().push_content_item(payload)
    return {
        "atos_post_id": str(post.id),
        "success": True,
        "created": bool(result.get("created")),
        "duplicate": bool(result.get("duplicate")),
        "studio_item_id": result.get("studio_item_id"),
        "status": result.get("status"),
        "source_type": result.get("source_type"),
        "error": None,
    }


@router.post("/push")
def push_post_to_studio(payload: StudioPushRequest, request: Request, db: Session = Depends(get_db)):
    try:
        result = _push_post_to_studio(
            db,
            atos_post_id=payload.atos_post_id,
            requested_content_type=payload.requested_content_type,
            target_platforms=payload.target_platforms,
            operator_note=payload.operator_note,
        )
        message = "已送入Studio内容池" if result["created"] else "该帖子已在Studio中，未重复创建"
        return ok(result, request.state.trace_id, message)
    except HTTPException:
        raise
    except StudioUnavailableError as exc:
        raise HTTPException(status_code=503, detail=exc.user_message) from exc
    except StudioAuthError as exc:
        raise HTTPException(status_code=502, detail=exc.user_message) from exc
    except StudioClientError as exc:
        raise HTTPException(status_code=502, detail=studio_error_summary(exc)) from exc


@router.post("/push-batch")
def push_posts_to_studio_batch(payload: StudioPushBatchRequest, request: Request, db: Session = Depends(get_db)):
    ordered_ids = list(dict.fromkeys(str(item) for item in payload.atos_post_ids if str(item).strip()))
    if not ordered_ids:
        raise HTTPException(status_code=422, detail="atos_post_ids cannot be empty")
    if len(ordered_ids) > 50:
        raise HTTPException(status_code=422, detail="batch size cannot exceed 50")

    results = []
    for post_id in ordered_ids:
        try:
            results.append(
                _push_post_to_studio(
                    db,
                    atos_post_id=post_id,
                    requested_content_type=payload.requested_content_type,
                    target_platforms=payload.target_platforms,
                    operator_note=payload.operator_note,
                )
            )
        except Exception as exc:
            results.append(
                {
                    "atos_post_id": post_id,
                    "success": False,
                    "created": False,
                    "duplicate": False,
                    "studio_item_id": None,
                    "status": None,
                    "source_type": None,
                    "error": studio_error_summary(exc) if not isinstance(exc, HTTPException) else str(exc.detail),
                }
            )

    summary = {
        "total": len(results),
        "created": sum(1 for item in results if item["success"] and item["created"]),
        "duplicates": sum(1 for item in results if item["success"] and item["duplicate"]),
        "failed": sum(1 for item in results if not item["success"]),
        "results": results,
    }
    return ok(summary, request.state.trace_id, "studio batch push completed")


@router.get("/status/{post_id}")
def studio_status_for_post(post_id: str, request: Request, db: Session = Depends(get_db)):
    post, platform = _find_post(db, post_id)
    try:
        result = StudioClient().get_source_status(
            source_platform=platform.slug,
            source_post_id=post.source_post_id,
            atos_post_id=str(post.id),
        )
        return ok({"atos_post_id": str(post.id), **result}, request.state.trace_id)
    except StudioUnavailableError as exc:
        return ok(
            {"atos_post_id": str(post.id), "exists": False, "status": "studio_unavailable", "error": exc.user_message},
            request.state.trace_id,
            "studio unavailable",
        )
    except StudioClientError as exc:
        return ok(
            {"atos_post_id": str(post.id), "exists": False, "status": "unknown", "error": studio_error_summary(exc)},
            request.state.trace_id,
            "studio status unavailable",
        )


@router.post("/status-batch")
def studio_status_for_posts(payload: dict, request: Request, db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(str(item) for item in payload.get("atos_post_ids", []) if str(item).strip()))
    if not ids:
        raise HTTPException(status_code=422, detail="atos_post_ids cannot be empty")
    if len(ids) > 200:
        raise HTTPException(status_code=422, detail="status batch size cannot exceed 200")
    items = []
    lookup: dict[str, str] = {}
    for post_id in ids:
        try:
            post, platform = _find_post(db, post_id)
            lookup[str(post.id)] = str(post.id)
            items.append({"source_platform": platform.slug, "source_post_id": post.source_post_id, "atos_post_id": str(post.id)})
        except HTTPException:
            continue
    try:
        studio_result = StudioClient().get_source_status_batch(items)
        return ok(studio_result, request.state.trace_id)
    except StudioUnavailableError as exc:
        return ok(
            {
                "items": [
                    {"atos_post_id": item["atos_post_id"], "exists": False, "status": "studio_unavailable", "error": exc.user_message}
                    for item in items
                ]
            },
            request.state.trace_id,
            "studio unavailable",
        )
    except StudioClientError as exc:
        return ok(
            {
                "items": [
                    {"atos_post_id": item["atos_post_id"], "exists": False, "status": "unknown", "error": studio_error_summary(exc)}
                    for item in items
                ]
            },
            request.state.trace_id,
            "studio status unavailable",
        )
