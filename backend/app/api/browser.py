from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BrowserSession, BrowserTab
from app.response import ok
from app.serializers import serialize_model
from app.services.browser_runtime import BrowserRuntime


router = APIRouter(prefix="/browser", tags=["browser"])


@router.get("/runtime")
def get_browser_runtime(request: Request, db: Session = Depends(get_db)):
    return ok(BrowserRuntime(db).runtime_status(), request.state.trace_id)


@router.get("/sessions")
def list_browser_sessions(request: Request, db: Session = Depends(get_db)):
    sessions = db.scalars(select(BrowserSession).order_by(BrowserSession.updated_at.desc())).all()
    return ok([serialize_model(session) for session in sessions], request.state.trace_id)


@router.get("/tabs")
def list_browser_tabs(request: Request, db: Session = Depends(get_db)):
    tabs = db.scalars(select(BrowserTab).order_by(BrowserTab.opened_at.desc())).all()
    return ok([serialize_model(tab) for tab in tabs], request.state.trace_id)


@router.post("/open", status_code=status.HTTP_201_CREATED)
def open_browser_url(payload: dict, request: Request, db: Session = Depends(get_db)):
    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    try:
        tab = BrowserRuntime(db).open_url(
            url=url,
            browser_type=str(payload.get("browser_type") or "mock"),
            worker_id=payload.get("worker_id"),
            account_id=payload.get("account_id"),
            profile_id=payload.get("profile_id"),
            execution_task_id=payload.get("execution_task_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(tab)
    return ok(serialize_model(tab), request.state.trace_id, "browser tab opened")


@router.post("/close")
def close_browser_tab(payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        tab = BrowserRuntime(db).close_tab(int(payload.get("tab_id")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(tab)
    return ok(serialize_model(tab), request.state.trace_id, "browser tab closed")


@router.post("/recover")
def recover_browser_session(payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        session = BrowserRuntime(db).recover(int(payload.get("session_id")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)
    return ok(serialize_model(session), request.state.trace_id, "browser session recovered")
