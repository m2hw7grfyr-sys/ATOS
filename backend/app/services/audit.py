from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    entity_type: str | None = None,
    entity_uuid: str | None = None,
    actor: str = "system",
    detail: dict[str, Any] | None = None,
    trace_id: str = "system",
) -> AuditLog:
    item = AuditLog(
        trace_id=trace_id,
        action=action,
        entity_type=entity_type,
        entity_uuid=entity_uuid,
        actor=actor,
        detail=detail or {},
    )
    db.add(item)
    db.flush()
    return item
