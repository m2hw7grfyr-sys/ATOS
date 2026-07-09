from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, TGEProfile
from app.response import ok
from app.schemas import AccountCreate
from app.serializers import serialize_model


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Account).order_by(Account.created_at.desc())).all()
    profiles = {
        profile.account_id: profile
        for profile in db.scalars(select(TGEProfile)).all()
    }
    result = []
    for item in items:
        serialized = serialize_model(item)
        profile = profiles.get(item.id)
        serialized["tge_profile"] = serialize_model(profile) if profile else None
        result.append(serialized)
    return ok(result, request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate, request: Request, db: Session = Depends(get_db)
):
    values = payload.model_dump()
    environment_id = values.pop("environment_id")
    environment_name = values.pop("environment_name")
    item = Account(**values, status="ACTIVE")
    db.add(item)
    db.flush()
    if environment_id:
        db.add(
            TGEProfile(
                account_id=item.id,
                environment_id=environment_id,
                name=environment_name or f"{item.username} environment",
                status="OFFLINE",
            )
        )
    db.commit()
    db.refresh(item)
    result = serialize_model(item)
    result["environment_id"] = environment_id
    return ok(result, request.state.trace_id, "account created")
