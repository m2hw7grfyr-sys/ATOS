from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, AccountLimit, AccountWorkingWindow, Platform, TGEProfile
from app.response import ok
from app.schemas import (
    AccountCreate,
    AccountLimitUpdate,
    AccountUpdate,
    AccountWorkingWindowsUpdate,
    BindTGEProfileRequest,
)
from app.serializers import serialize_model


router = APIRouter(prefix="/accounts", tags=["accounts"])


def ensure_limits(db: Session, account: Account) -> AccountLimit:
    item = db.scalar(select(AccountLimit).where(AccountLimit.account_id == account.id))
    if not item:
        limits = account.daily_limits or {}
        item = AccountLimit(
            account_id=account.id,
            browse_daily_limit=int(limits.get("browse", 20)),
            like_daily_limit=int(limits.get("like", 8)),
            bookmark_daily_limit=int(limits.get("bookmark", 5)),
            visit_profile_daily_limit=int(limits.get("visit_profile", 5)),
            reply_daily_limit=int(limits.get("reply", 5)),
        )
        db.add(item)
        db.flush()
    return item


def ensure_windows(db: Session, account: Account) -> list[AccountWorkingWindow]:
    items = db.scalars(
        select(AccountWorkingWindow)
        .where(AccountWorkingWindow.account_id == account.id)
        .order_by(AccountWorkingWindow.day_of_week, AccountWorkingWindow.start_time)
    ).all()
    if items:
        return items
    raw_windows = []
    working_time = account.working_time or {}
    if isinstance(working_time, dict):
        raw_windows = working_time.get("windows", [])
    elif isinstance(working_time, list):
        raw_windows = working_time
    for raw in raw_windows:
        item = AccountWorkingWindow(
            account_id=account.id,
            day_of_week=str(raw.get("day", "MON")).upper(),
            start_time=str(raw.get("start", "09:00")),
            end_time=str(raw.get("end", "18:00")),
            timezone=str(raw.get("timezone", working_time.get("timezone", "Asia/Shanghai") if isinstance(working_time, dict) else "Asia/Shanghai")),
            enabled=bool(raw.get("enabled", True)),
        )
        db.add(item)
        items.append(item)
    db.flush()
    return items


def serialize_account(account: Account, db: Session) -> dict:
    item = serialize_model(account)
    platform = db.get(Platform, account.platform_id)
    profile = db.scalar(
        select(TGEProfile).where(
            (TGEProfile.bound_account_id == account.id) | (TGEProfile.account_id == account.id)
        )
    )
    limits = ensure_limits(db, account)
    windows = ensure_windows(db, account)
    item["platform"] = platform.slug if platform else None
    item["platform_name"] = platform.name if platform else None
    item["risk_status"] = account.risk_status or account.risk_level
    item["tge_profile"] = serialize_model(profile) if profile else None
    item["tge_environment_id"] = (
        profile.tge_environment_id or profile.environment_id if profile else None
    )
    item["limits"] = serialize_model(limits)
    item["working_windows"] = [serialize_model(window) for window in windows]
    return item


@router.get("")
def list_accounts(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Account).order_by(Account.created_at.desc())).all()
    result = [serialize_account(item, db) for item in items]
    db.commit()
    return ok(result, request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate, request: Request, db: Session = Depends(get_db)
):
    values = payload.model_dump()
    environment_id = values.pop("environment_id", None)
    environment_name = values.pop("environment_name", None)
    item = Account(**values, risk_level=values.get("risk_status", "LOW"), status="ACTIVE")
    db.add(item)
    db.flush()
    ensure_limits(db, item)
    ensure_windows(db, item)
    if environment_id:
        profile = TGEProfile(
            account_id=item.id,
            bound_account_id=item.id,
            platform_id=item.platform_id,
            environment_id=environment_id,
            tge_environment_id=environment_id,
            name=environment_name or f"{item.username} environment",
            profile_name=environment_name or f"{item.username} environment",
            status="ACTIVE",
        )
        db.add(profile)
    db.commit()
    db.refresh(item)
    return ok(serialize_account(item, db), request.state.trace_id, "account created")


@router.get("/{account_id}")
def get_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Account, account_id)
    if not item:
        raise HTTPException(status_code=404, detail="account not found")
    result = serialize_account(item, db)
    db.commit()
    return ok(result, request.state.trace_id)


@router.put("/{account_id}")
def update_account(
    account_id: int,
    payload: AccountUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = db.get(Account, account_id)
    if not item:
        raise HTTPException(status_code=404, detail="account not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(item, key, value)
    if "risk_status" in updates:
        item.risk_level = str(updates["risk_status"])
    db.commit()
    db.refresh(item)
    return ok(serialize_account(item, db), request.state.trace_id, "account updated")


@router.post("/{account_id}/pause")
def pause_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Account, account_id)
    if not item:
        raise HTTPException(status_code=404, detail="account not found")
    item.status = "PAUSED"
    db.commit()
    return ok(serialize_account(item, db), request.state.trace_id, "account paused")


@router.post("/{account_id}/resume")
def resume_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Account, account_id)
    if not item:
        raise HTTPException(status_code=404, detail="account not found")
    item.status = "ACTIVE"
    db.commit()
    return ok(serialize_account(item, db), request.state.trace_id, "account resumed")


@router.post("/{account_id}/recalculate-health")
def recalculate_health(account_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Account, account_id)
    if not item:
        raise HTTPException(status_code=404, detail="account not found")
    score = 100
    score -= int(item.failure_count_24h or 0) * 5
    score -= int(item.restriction_count_7d or 0) * 20
    if item.cooling_down_until:
        score -= 10
    item.health_score = max(0, min(100, score))
    db.commit()
    return ok(serialize_account(item, db), request.state.trace_id, "health recalculated")


@router.post("/{account_id}/bind-tge-profile")
def bind_tge_profile(
    account_id: int,
    payload: BindTGEProfileRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    profile = db.get(TGEProfile, payload.profile_id)
    if not account or not profile:
        raise HTTPException(status_code=404, detail="account or profile not found")
    existing_account_profile = db.scalar(
        select(TGEProfile).where(
            TGEProfile.bound_account_id == account.id,
            TGEProfile.id != profile.id,
        )
    )
    if existing_account_profile:
        raise HTTPException(status_code=409, detail="account already bound")
    if profile.bound_account_id and profile.bound_account_id != account.id:
        raise HTTPException(status_code=409, detail="profile already bound")
    profile.bound_account_id = account.id
    profile.account_id = account.id
    profile.platform_id = account.platform_id
    db.commit()
    return ok(serialize_account(account, db), request.state.trace_id, "TGE profile bound")


@router.delete("/{account_id}/unbind-tge-profile")
def unbind_tge_profile(account_id: int, request: Request, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    profile = db.scalar(select(TGEProfile).where(TGEProfile.bound_account_id == account.id))
    if profile:
        profile.bound_account_id = None
        profile.account_id = None
    db.commit()
    return ok(serialize_account(account, db), request.state.trace_id, "TGE profile unbound")


@router.get("/{account_id}/limits")
def get_limits(account_id: int, request: Request, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    item = ensure_limits(db, account)
    db.commit()
    return ok(serialize_model(item), request.state.trace_id)


@router.put("/{account_id}/limits")
def update_limits(
    account_id: int,
    payload: AccountLimitUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    item = ensure_limits(db, account)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    account.daily_limits = {
        "browse": item.browse_daily_limit,
        "like": item.like_daily_limit,
        "bookmark": item.bookmark_daily_limit,
        "visit_profile": item.visit_profile_daily_limit,
        "reply": item.reply_daily_limit,
    }
    db.commit()
    return ok(serialize_model(item), request.state.trace_id, "limits updated")


@router.get("/{account_id}/working-windows")
def get_working_windows(account_id: int, request: Request, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    items = ensure_windows(db, account)
    db.commit()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.put("/{account_id}/working-windows")
def update_working_windows(
    account_id: int,
    payload: AccountWorkingWindowsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    db.execute(delete(AccountWorkingWindow).where(AccountWorkingWindow.account_id == account.id))
    windows = []
    for raw in payload.windows:
        window = AccountWorkingWindow(
            account_id=account.id,
            day_of_week=str(raw.get("day_of_week", raw.get("day", "MON"))).upper(),
            start_time=str(raw.get("start_time", raw.get("start", "09:00"))),
            end_time=str(raw.get("end_time", raw.get("end", "18:00"))),
            timezone=str(raw.get("timezone", "Asia/Shanghai")),
            enabled=bool(raw.get("enabled", True)),
        )
        db.add(window)
        windows.append(window)
    account.working_time = {
        "timezone": windows[0].timezone if windows else "Asia/Shanghai",
        "windows": [
            {
                "day": item.day_of_week,
                "start": item.start_time,
                "end": item.end_time,
                "timezone": item.timezone,
                "enabled": item.enabled,
            }
            for item in windows
        ],
    }
    db.commit()
    return ok([serialize_model(item) for item in windows], request.state.trace_id, "working windows updated")
