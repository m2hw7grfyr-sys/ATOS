from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SystemSetting
from app.response import ok
from app.schemas import SettingUpdate
from app.serializers import serialize_model


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def list_settings(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)).all()
    safe_items = []
    for item in items:
        serialized = serialize_model(item)
        if item.is_secret:
            serialized["value"] = {"configured": bool(item.value)}
        safe_items.append(serialized)
    return ok(safe_items, request.state.trace_id)


@router.put("/{key}")
def update_setting(
    key: str,
    payload: SettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not item:
        raise HTTPException(status_code=404, detail="setting not found")
    item.value = payload.value
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "setting updated")
