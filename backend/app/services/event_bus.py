from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import BusinessEvent


class LocalEventBus:
    """Local event sink used before Redis or an external event bus exists."""

    def publish(
        self,
        db: Session,
        event_name: str,
        *,
        entity_type: str,
        entity_id: int | None = None,
        post_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> BusinessEvent:
        event = BusinessEvent(
            event_name=event_name,
            entity_type=entity_type,
            entity_id=entity_id,
            post_id=post_id,
            payload=payload or {},
        )
        db.add(event)
        db.flush()
        return event
