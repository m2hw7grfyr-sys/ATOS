from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AITask, Account, Platform, Post, Reply, SchedulerLog, SchedulerTask
from app.response import ok
from app.schemas import (
    SchedulerApprovedTaskCreate,
    SchedulerBulkApprovedCreate,
    SchedulerTaskCreate,
)
from app.serializers import serialize_model
from app.services.scheduler import queue_approved_ai_task, run_once, set_status


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def serialize_scheduler_task(task: SchedulerTask, db: Session) -> dict:
    item = serialize_model(task)
    platform = db.get(Platform, task.platform_id)
    post = db.get(Post, task.post_id) if task.post_id else None
    account = db.get(Account, task.account_id) if task.account_id else None
    reply = db.get(Reply, task.reply_id) if task.reply_id else None
    ai_task = db.get(AITask, reply.ai_task_id) if reply and reply.ai_task_id else None
    item["task_id"] = task.id
    item["platform"] = platform.slug if platform else None
    item["post_title"] = post.title if post else None
    item["account"] = account.username if account else None
    item["strategy"] = ai_task.strategy if ai_task else (task.payload or {}).get("strategy")
    item["strategy_type"] = (task.payload or {}).get("strategy_type")
    item["action_type"] = (task.payload or {}).get("action_type")
    item["parent_task_id"] = (task.payload or {}).get("parent_task_id")
    return item


@router.get("/tasks")
def list_scheduler_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(
        select(SchedulerTask).order_by(SchedulerTask.created_at.desc())
    ).all()
    return ok([serialize_scheduler_task(item, db) for item in items], request.state.trace_id)


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_scheduler_task(
    payload: SchedulerTaskCreate, request: Request, db: Session = Depends(get_db)
):
    if payload.reply_id:
        reply = db.get(Reply, payload.reply_id)
        if not reply or reply.status != "APPROVED":
            raise HTTPException(status_code=409, detail="reply must be approved")
    item = SchedulerTask(**payload.model_dump(), status="NEW")
    db.add(item)
    db.flush()
    set_status(db, item, "QUEUED", action="MANUAL_CREATE", reason="Manual scheduler task created")
    db.commit()
    db.refresh(item)
    return ok(serialize_scheduler_task(item, db), request.state.trace_id, "task queued")


@router.post("/tasks/from-approved", status_code=status.HTTP_201_CREATED)
def queue_approved_task(
    payload: SchedulerApprovedTaskCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        item = queue_approved_ai_task(
            db,
            ai_task_id=payload.ai_task_id,
            account_id=payload.account_id,
            priority=payload.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(item)
    return ok(serialize_scheduler_task(item, db), request.state.trace_id, "approved task queued")


@router.post("/tasks/bulk-from-approved")
def bulk_queue_approved(
    payload: SchedulerBulkApprovedCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    query = select(AITask).where(AITask.status == "APPROVED")
    if payload.post_ids:
        query = query.where(AITask.post_id.in_(payload.post_ids))
    queued = []
    skipped = 0
    for ai_task in db.scalars(query).all():
        try:
            queued.append(
                queue_approved_ai_task(
                    db,
                    ai_task_id=ai_task.id,
                    priority=payload.priority,
                )
            )
        except ValueError:
            skipped += 1
    db.commit()
    return ok(
        {
            "queued_count": len(queued),
            "skipped_count": skipped,
            "tasks": [serialize_scheduler_task(item, db) for item in queued],
        },
        request.state.trace_id,
        "approved tasks queued",
    )


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(SchedulerTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    set_status(db, task, "CANCELLED", action="CANCEL", reason="Cancelled manually")
    db.commit()
    db.refresh(task)
    return ok(serialize_scheduler_task(task, db), request.state.trace_id, "task cancelled")


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(SchedulerTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    task.error_message = None
    task.delay_seconds = 0
    task.earliest_execute_at = None
    set_status(db, task, "QUEUED", action="RETRY", reason="Retry manually")
    db.commit()
    db.refresh(task)
    return ok(serialize_scheduler_task(task, db), request.state.trace_id, "task queued for retry")


@router.post("/run-once")
def run_scheduler_once(request: Request, db: Session = Depends(get_db)):
    result = run_once(db)
    return ok(result, request.state.trace_id, "scheduler run once completed")


@router.get("/logs")
def list_scheduler_logs(request: Request, db: Session = Depends(get_db)):
    logs = db.scalars(select(SchedulerLog).order_by(SchedulerLog.created_at.desc()).limit(100)).all()
    return ok([serialize_model(item) for item in logs], request.state.trace_id)
