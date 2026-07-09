from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DataSource
from app.response import ok
from app.schemas import DataSourceCreate
from app.serializers import serialize_model


router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("")
def list_data_sources(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(DataSource).order_by(DataSource.created_at.desc())).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_data_source(
    payload: DataSourceCreate, request: Request, db: Session = Depends(get_db)
):
    item = DataSource(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "data source created")
