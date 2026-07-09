from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StatisticSnapshot
from app.response import ok
from app.serializers import serialize_model


router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("")
def list_statistics(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(
        select(StatisticSnapshot).order_by(StatisticSnapshot.metric)
    ).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)
