from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.response import ok
from app.schemas import PipelineBatchRequest, PipelinePostRequest, PipelineRunRequest
from app.services.pipeline import BusinessPipelineService


router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def pipeline_service(request: Request, db: Session) -> BusinessPipelineService:
    return BusinessPipelineService(
        db,
        actor="operator",
        trace_id=getattr(request.state, "trace_id", "system"),
    )


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_pipeline(
    payload: PipelineRunRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    service = pipeline_service(request, db)
    result: dict = {}
    try:
        if payload.data_source_id is not None:
            result["data_source"] = service.run_data_source(payload.data_source_id)
        post_ids = payload.post_ids
        if payload.auto_analyze and post_ids:
            result["posts"] = [
                service.run_post(
                    post_id,
                    auto_approve=payload.auto_approve,
                    send_to_scheduler=payload.send_to_scheduler,
                )
                for post_id in post_ids
            ]
        result["status"] = service.status()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ok(result, request.state.trace_id, "pipeline run accepted")


@router.post("/post/{post_id}", status_code=status.HTTP_202_ACCEPTED)
def run_post_pipeline(
    post_id: int,
    payload: PipelinePostRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    service = pipeline_service(request, db)
    action = payload.action.upper()
    try:
        if action == "RUN":
            result = service.run_post(
                post_id,
                auto_approve=payload.auto_approve,
                send_to_scheduler=payload.send_to_scheduler,
            )
        elif action == "ANALYZE":
            result = service.analyze_post(post_id)
        elif action == "APPROVE":
            result = service.approve_post(post_id)
        elif action == "REJECT":
            result = service.reject_post(post_id)
        elif action == "ARCHIVE":
            result = service.archive_post(post_id)
        elif action in {"SEND_TO_SCHEDULER", "SCHEDULE"}:
            result = service.send_to_scheduler(post_id, priority=payload.priority)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {payload.action}")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ok(result, request.state.trace_id, "pipeline post action completed")


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
def run_pipeline_batch(
    payload: PipelineBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = pipeline_service(request, db).batch(
        payload.post_ids,
        payload.action,
        priority=payload.priority,
    )
    return ok(result, request.state.trace_id, "pipeline batch action completed")


@router.get("/status")
def pipeline_status(request: Request, db: Session = Depends(get_db)):
    return ok(pipeline_service(request, db).status(), request.state.trace_id)
