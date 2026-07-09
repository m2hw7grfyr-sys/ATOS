from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AITask
from app.response import ok
from app.serializers import serialize_model


router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/tasks")
def list_ai_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(AITask).order_by(AITask.created_at.desc())).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)
