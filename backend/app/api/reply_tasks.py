from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, ExecutionTask, Platform, Post, Reply, ReplyTask, SchedulerTask
from app.response import ok
from app.serializers import serialize_model
from app.services.reply_pipeline import ReplyPipelineService


router = APIRouter(prefix="/reply-tasks", tags=["reply-tasks"])


def serialize_reply_task(task: ReplyTask, db: Session) -> dict:
    item = serialize_model(task)
    post = db.get(Post, task.post_id)
    reply = db.get(Reply, task.reply_id)
    scheduler_task = db.get(SchedulerTask, task.scheduler_task_id) if task.scheduler_task_id else None
    execution_task = db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
    account = db.get(Account, task.account_id) if task.account_id else None
    platform = db.get(Platform, post.platform_id) if post and post.platform_id else None
    item["post_title"] = post.title if post else None
    item["post_url"] = post.url if post else None
    item["reply_status"] = reply.status if reply else None
    item["scheduler_status"] = scheduler_task.status if scheduler_task else None
    item["execution_status"] = execution_task.status if execution_task else None
    item["account"] = account.username if account else None
    item["platform"] = item.get("platform") or (platform.slug if platform else None)
    item["message"] = "Reply prepared. Waiting for manual confirmation." if task.status == "WAITING_MANUAL" else None
    return item


@router.get("")
def list_reply_tasks(request: Request, db: Session = Depends(get_db)):
    tasks = db.scalars(select(ReplyTask).order_by(ReplyTask.created_at.desc())).all()
    return ok([serialize_reply_task(task, db) for task in tasks], request.state.trace_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reply_task(payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        task = ReplyPipelineService(db, trace_id=request.state.trace_id).create_reply_task(
            reply_id=int(payload.get("reply_id")),
            account_id=payload.get("account_id"),
            execution_mode=str(payload.get("execution_mode") or "SEMI_AUTO"),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_reply_task(task, db), request.state.trace_id, "reply task created")


@router.post("/{reply_task_id}/approve")
def approve_reply_task(reply_task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ReplyTask, reply_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="reply task not found")
    try:
        task = ReplyPipelineService(db, trace_id=request.state.trace_id).approve_reply(
            reply_id=task.reply_id,
            account_id=task.account_id,
            execution_mode=task.execution_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_reply_task(task, db), request.state.trace_id, "reply task approved")


@router.post("/{reply_task_id}/schedule")
def schedule_reply_task(reply_task_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        scheduler_task = ReplyPipelineService(db, trace_id=request.state.trace_id).schedule_reply_task(
            reply_task_id,
            account_id=payload.get("account_id"),
            priority=str(payload.get("priority") or "MEDIUM"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    reply_task = db.get(ReplyTask, reply_task_id)
    return ok(
        {
            "reply_task": serialize_reply_task(reply_task, db) if reply_task else None,
            "scheduler_task": serialize_model(scheduler_task),
        },
        request.state.trace_id,
        "reply task scheduled",
    )


@router.post("/{reply_task_id}/prepare")
def prepare_reply_task(reply_task_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        task = ReplyPipelineService(db, trace_id=request.state.trace_id).prepare_reply(reply_task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_reply_task(task, db), request.state.trace_id, "reply prepared")


@router.post("/{reply_task_id}/confirm")
def confirm_reply_task(reply_task_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        task = ReplyPipelineService(db, trace_id=request.state.trace_id).confirm(reply_task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_reply_task(task, db), request.state.trace_id, "reply task confirmed")
