from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SchedulerTask
from app.response import ok
from app.schemas import SchedulerTaskCreate
from app.serializers import serialize_model


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/tasks")
def list_scheduler_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(
        select(SchedulerTask).order_by(SchedulerTask.created_at.desc())
    ).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_scheduler_task(
    payload: SchedulerTaskCreate, request: Request, db: Session = Depends(get_db)
):
    item = SchedulerTask(**payload.model_dump(), status="QUEUED")
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "task queued")
