from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlatformSelector
from app.response import ok
from app.schemas import PlatformSelectorCreate, PlatformSelectorUpdate
from app.serializers import serialize_model


router = APIRouter(prefix="/platform-selectors", tags=["platform-selectors"])


@router.get("")
def list_platform_selectors(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(
        select(PlatformSelector).order_by(
            PlatformSelector.platform.asc(),
            PlatformSelector.selector_key.asc(),
            PlatformSelector.id.asc(),
        )
    ).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_platform_selector(
    payload: PlatformSelectorCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = PlatformSelector(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "selector created")


@router.put("/{selector_id}")
def update_platform_selector(
    selector_id: int,
    payload: PlatformSelectorUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = db.get(PlatformSelector, selector_id)
    if not item:
        raise HTTPException(status_code=404, detail="selector not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "selector updated")
