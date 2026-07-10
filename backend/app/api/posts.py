from __future__ import annotations

from typing import Optional

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActorMapping, DataSource, FilterPreset, Platform, Post, PostTimeline
from app.response import ok
from app.schemas import FilterPresetCreate, PostBatchRequest
from app.serializers import serialize_model
from app.services.pipeline import BusinessPipelineService


router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("")
def list_posts(
    request: Request,
    platform: Optional[str] = Query(default=None),
    source_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    community: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    base_statement = (
        select(Post, Platform, DataSource)
        .join(Platform, Platform.id == Post.platform_id)
        .outerjoin(DataSource, DataSource.id == Post.data_source_id)
    )
    if platform:
        base_statement = base_statement.where(Platform.slug == platform.lower())
    if source_id is not None:
        base_statement = base_statement.where(Post.data_source_id == source_id)
    if status:
        base_statement = base_statement.where(Post.status == status.upper())
    if community:
        base_statement = base_statement.where(Post.community.ilike(f"%{community}%"))
    if keyword:
        pattern = f"%{keyword}%"
        base_statement = base_statement.where(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern),
                Post.author.ilike(pattern),
                Post.community.ilike(pattern),
            )
        )
    if date_from:
        base_statement = base_statement.where(Post.created_at >= date_from)
    if date_to:
        base_statement = base_statement.where(Post.created_at <= date_to)

    count_statement = select(func.count()).select_from(base_statement.subquery())
    total = db.scalar(count_statement) or 0
    sortable = {
        "created_at": Post.created_at,
        "published_at": Post.published_at,
        "score": Post.score,
        "comment_count": Post.comment_count,
        "status": Post.status,
    }
    sort_column = sortable.get(sort_by, Post.created_at)
    if sort_dir.lower() == "asc":
        base_statement = base_statement.order_by(sort_column.asc())
    else:
        base_statement = base_statement.order_by(sort_column.desc())
    offset = (page - 1) * page_size
    statement = base_statement.offset(offset).limit(min(limit, page_size))

    rows = db.execute(statement).all()
    items = []
    for post, post_platform, source in rows:
        serialized = serialize_model(post)
        serialized["platform"] = post_platform.slug
        serialized["source"] = source.name if source else None
        serialized["source_name"] = source.name if source else None
        serialized["actor_name"] = (source.config or {}).get("actor_name") if source else None
        mapping = db.get(ActorMapping, post.mapping_id) if post.mapping_id else None
        serialized["mapping_name"] = mapping.mapping_name if mapping else None
        items.append(serialized)
    return ok(
        {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size if page_size else 1,
            },
        },
        request.state.trace_id,
    )


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
def batch_posts(
    payload: PostBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = BusinessPipelineService(
        db,
        actor="operator",
        trace_id=request.state.trace_id,
    ).batch(payload.post_ids, payload.action, priority=payload.priority)
    return ok(result, request.state.trace_id, "post batch action completed")


@router.get("/filter-presets")
def list_filter_presets(
    request: Request,
    scope: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    statement = select(FilterPreset).where(FilterPreset.status == "ACTIVE")
    if scope:
        statement = statement.where(FilterPreset.scope == scope.upper())
    items = db.scalars(statement.order_by(FilterPreset.created_at.desc())).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("/filter-presets", status_code=status.HTTP_201_CREATED)
def create_filter_preset(
    payload: FilterPresetCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = FilterPreset(
        name=payload.name,
        scope=payload.scope.upper(),
        filters=payload.filters,
        actor="operator",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "filter preset saved")


@router.get("/{post_id}/timeline")
def post_timeline(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    rows = db.scalars(
        select(PostTimeline)
        .where(PostTimeline.post_id == post_id)
        .order_by(PostTimeline.created_at.asc())
    ).all()
    return ok([serialize_model(item) for item in rows], request.state.trace_id)
