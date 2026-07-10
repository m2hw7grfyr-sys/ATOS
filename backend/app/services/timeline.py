from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Post, PostTimeline, utc_now
from app.services.event_bus import LocalEventBus


STATUS_EVENTS = {
    "NORMALIZED": "PostNormalized",
    "READY_FOR_AI": "PostReadyForAI",
    "ANALYZING": "PostAnalyzing",
    "AI_COMPLETED": "AICompleted",
    "WAITING_REVIEW": "PostWaitingReview",
    "APPROVED": "ReplyApproved",
    "SCHEDULED": "TaskScheduled",
    "ARCHIVED": "PostArchived",
}


def set_post_status(
    db: Session,
    post: Post,
    new_status: str,
    *,
    event_name: str | None = None,
    actor: str = "system",
    detail: dict[str, Any] | None = None,
    publish_event: bool = True,
) -> PostTimeline:
    old_status = post.status
    now = utc_now()
    post.status = new_status
    post.pipeline_stage = new_status
    if new_status == "READY_FOR_AI":
        post.ready_for_ai_at = now
    elif new_status == "AI_COMPLETED":
        post.ai_completed_at = now
    elif new_status in {"APPROVED", "REJECTED"}:
        post.reviewed_at = now
    elif new_status == "SCHEDULED":
        post.scheduled_at = now
    elif new_status == "ARCHIVED":
        post.archived_at = now

    timeline = PostTimeline(
        post_id=post.id,
        event_name=event_name or STATUS_EVENTS.get(new_status, "PostStatusChanged"),
        old_status=old_status,
        new_status=new_status,
        actor=actor,
        detail=detail or {},
    )
    db.add(timeline)
    db.flush()
    if publish_event:
        LocalEventBus().publish(
            db,
            timeline.event_name,
            entity_type="Post",
            entity_id=post.id,
            post_id=post.id,
            payload={"old_status": old_status, "new_status": new_status, **(detail or {})},
        )
    return timeline
