from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActorMapping
from app.response import ok
from app.schemas import ActorMappingCreate, ActorMappingTestRequest, ActorMappingUpdate
from app.serializers import serialize_model
from app.services.apify import mapping_preview


router = APIRouter(prefix="/actor-mappings", tags=["actor-mappings"])


@router.get("")
def list_actor_mappings(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(ActorMapping).order_by(ActorMapping.created_at.desc())).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_actor_mapping(payload: ActorMappingCreate, request: Request, db: Session = Depends(get_db)):
    item = ActorMapping(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "actor mapping created")


@router.put("/{mapping_id}")
def update_actor_mapping(mapping_id: int, payload: ActorMappingUpdate, request: Request, db: Session = Depends(get_db)):
    item = db.get(ActorMapping, mapping_id)
    if not item:
        raise HTTPException(status_code=404, detail="actor mapping not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "actor mapping updated")


@router.post("/test")
def test_actor_mapping(payload: ActorMappingTestRequest, request: Request):
    return ok(
        mapping_preview(payload.mapping, payload.raw_item_json),
        request.state.trace_id,
        "actor mapping tested",
    )
