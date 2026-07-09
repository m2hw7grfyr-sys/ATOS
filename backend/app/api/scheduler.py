from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AITask, Post, Reply, SchedulerTask
from app.response import ok
from app.schemas import SchedulerApprovedTaskCreate, SchedulerTaskCreate
from app.serializers import serialize_model


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/tasks")
def list_scheduler_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(
        select(SchedulerTask).order_by(SchedulerTask.created_at.desc())
    ).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_scheduler_task(
    payload: SchedulerTaskCreate, request: Request, db: Session = Depends(get_db)
):
    if payload.reply_id:
        reply = db.get(Reply, payload.reply_id)
        if not reply or reply.status != "APPROVED":
            raise HTTPException(status_code=409, detail="reply must be approved")
    item = SchedulerTask(**payload.model_dump(), status="QUEUED")
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "task queued")


@router.post("/tasks/from-approved", status_code=status.HTTP_201_CREATED)
def queue_approved_task(
    payload: SchedulerApprovedTaskCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    ai_task = db.get(AITask, payload.ai_task_id)
    if not ai_task or ai_task.status != "APPROVED":
        raise HTTPException(status_code=409, detail="AI task must be approved")
    reply = db.scalar(select(Reply).where(Reply.ai_task_id == ai_task.id))
    post = db.get(Post, ai_task.post_id)
    if not reply or reply.status != "APPROVED" or not post:
        raise HTTPException(status_code=409, detail="approved reply or post missing")
    existing = db.scalar(
        select(SchedulerTask).where(
            SchedulerTask.reply_id == reply.id,
            SchedulerTask.status.in_(["QUEUED", "DELAYED", "RUNNING"]),
        )
    )
    if existing:
        return ok(
            serialize_model(existing),
            request.state.trace_id,
            "task already queued",
        )
    item = SchedulerTask(
        task_type="REPLY",
        platform_id=post.platform_id,
        account_id=payload.account_id,
        post_id=post.id,
        reply_id=reply.id,
        priority=payload.priority.upper(),
        payload={"ai_task_id": ai_task.id, "mode": "HUMAN_IN_THE_LOOP"},
        status="QUEUED",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "approved task queued")
