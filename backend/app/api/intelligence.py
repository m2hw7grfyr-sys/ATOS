from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IntelligenceRecommendation, ReplySimilarity
from app.response import ok
from app.serializers import serialize_model
from app.services.intelligence_runtime import IntelligenceRuntime


router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    data = IntelligenceRuntime(db).collect_performance()
    db.commit()
    return ok(data, request.state.trace_id)


@router.get("/recommendations")
def recommendations(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(IntelligenceRecommendation)
        .order_by(IntelligenceRecommendation.score.desc(), IntelligenceRecommendation.created_at.desc())
        .limit(100)
    ).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)


@router.get("/performance")
def performance(request: Request, db: Session = Depends(get_db)):
    runtime = IntelligenceRuntime(db)
    runtime.collect_performance()
    data = runtime.performance()
    db.commit()
    return ok(data, request.state.trace_id)


@router.post("/score")
def score(payload: dict, request: Request, db: Session = Depends(get_db)):
    reply_id = payload.get("reply_id")
    if not reply_id:
        raise HTTPException(status_code=400, detail="reply_id is required")
    try:
        score_row = IntelligenceRuntime(db).score_reply(int(reply_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(score_row)
    return ok(serialize_model(score_row), request.state.trace_id, "reply scored")


@router.post("/feedback")
def feedback(payload: dict, request: Request, db: Session = Depends(get_db)):
    recommendation = IntelligenceRuntime(db).feedback(payload)
    db.commit()
    db.refresh(recommendation)
    return ok(serialize_model(recommendation), request.state.trace_id, "feedback captured")


@router.post("/similarity")
def similarity(payload: dict, request: Request, db: Session = Depends(get_db)):
    threshold = float(payload.get("threshold") or 85)
    rows = IntelligenceRuntime(db).detect_duplicate_replies(threshold)
    db.commit()
    return ok([serialize_model(row) for row in rows], request.state.trace_id, "similarity checked")


@router.get("/similarity")
def list_similarity(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ReplySimilarity)
        .order_by(ReplySimilarity.similarity_score.desc(), ReplySimilarity.created_at.desc())
        .limit(100)
    ).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)
