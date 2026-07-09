from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, Platform, TGEProfile
from app.response import ok
from app.schemas import TGEProfileCreate, TGEProfileUpdate
from app.serializers import serialize_model


router = APIRouter(prefix="/tge-profiles", tags=["tge-profiles"])


def serialize_profile(profile: TGEProfile, db: Session) -> dict:
    item = serialize_model(profile)
    platform = db.get(Platform, profile.platform_id) if profile.platform_id else None
    account = (
        db.get(Account, profile.bound_account_id or profile.account_id)
        if (profile.bound_account_id or profile.account_id)
        else None
    )
    item["platform"] = platform.slug if platform else None
    item["platform_name"] = platform.name if platform else None
    item["bound_account"] = account.username if account else None
    return item


@router.get("")
def list_tge_profiles(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(TGEProfile).order_by(TGEProfile.created_at.desc())).all()
    return ok([serialize_profile(item, db) for item in items], request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_tge_profile(
    payload: TGEProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    if payload.bound_account_id:
        existing = db.scalar(
            select(TGEProfile).where(TGEProfile.bound_account_id == payload.bound_account_id)
        )
        if existing:
            raise HTTPException(status_code=409, detail="account already bound")
    item = TGEProfile(
        profile_name=payload.profile_name,
        name=payload.profile_name,
        tge_environment_id=payload.tge_environment_id,
        environment_id=payload.tge_environment_id,
        platform_id=payload.platform_id,
        bound_account_id=payload.bound_account_id,
        account_id=payload.bound_account_id,
        proxy_region=payload.proxy_region,
        proxy_type=payload.proxy_type,
        status=payload.status,
        remark=payload.remark,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_profile(item, db), request.state.trace_id, "TGE profile created")


@router.put("/{profile_id}")
def update_tge_profile(
    profile_id: int,
    payload: TGEProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = db.get(TGEProfile, profile_id)
    if not item:
        raise HTTPException(status_code=404, detail="TGE profile not found")
    updates = payload.model_dump(exclude_unset=True)
    if "bound_account_id" in updates and updates["bound_account_id"]:
        existing = db.scalar(
            select(TGEProfile).where(
                TGEProfile.bound_account_id == updates["bound_account_id"],
                TGEProfile.id != item.id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="account already bound")
    for key, value in updates.items():
        setattr(item, key, value)
        if key == "profile_name":
            item.name = value
        if key == "tge_environment_id":
            item.environment_id = value
        if key == "bound_account_id":
            item.account_id = value
    db.commit()
    db.refresh(item)
    return ok(serialize_profile(item, db), request.state.trace_id, "TGE profile updated")
