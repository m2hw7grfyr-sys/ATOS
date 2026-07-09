from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Post
from app.response import ok
from app.serializers import serialize_model


router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("")
def list_posts(
    request: Request,
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    statement = select(Post).order_by(Post.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(Post.status == status.upper())
    items = db.scalars(statement).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)
