from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.response import ok
from app.schemas import AccountCreate
from app.serializers import serialize_model


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Account).order_by(Account.created_at.desc())).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate, request: Request, db: Session = Depends(get_db)
):
    item = Account(**payload.model_dump(), status="ACTIVE")
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "account created")
