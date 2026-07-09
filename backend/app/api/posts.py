from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DataSource, Platform, Post
from app.response import ok
from app.serializers import serialize_model


router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("")
def list_posts(
    request: Request,
    platform: Optional[str] = Query(default=None),
    source_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    statement = (
        select(Post, Platform, DataSource)
        .join(Platform, Platform.id == Post.platform_id)
        .outerjoin(DataSource, DataSource.id == Post.data_source_id)
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    if platform:
        statement = statement.where(Platform.slug == platform.lower())
    if source_id is not None:
        statement = statement.where(Post.data_source_id == source_id)
    if status:
        statement = statement.where(Post.status == status.upper())

    rows = db.execute(statement).all()
    items = []
    for post, post_platform, source in rows:
        serialized = serialize_model(post)
        serialized["platform"] = post_platform.slug
        serialized["source"] = source.name if source else None
        items.append(serialized)
    return ok(items, request.state.trace_id)
