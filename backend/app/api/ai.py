from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIAnalysisResult, AITask, Post, Reply
from app.response import ok
from app.schemas import AIBatchRequest, MockAIGenerateRequest, PromptPreviewRequest, ReplyGenerateRequest, ReplyUpdate
from app.serializers import serialize_model
from app.services.ai import AIAnalysisService, AIProviderError, ReplyGenerationService, preview_prompt
from app.services.audit import write_audit
from app.services.pipeline import BusinessPipelineService
from app.services.scheduler import get_scheduler_settings, queue_approved_ai_task
from app.services.timeline import set_post_status


router = APIRouter(prefix="/ai", tags=["ai"])


def serialize_task(task: AITask, db: Session) -> dict:
    serialized = serialize_model(task)
    reply = db.scalar(
        select(Reply)
        .where(Reply.ai_task_id == task.id)
        .order_by(Reply.version.desc(), Reply.id.desc())
    )
    analysis = db.scalar(
        select(AIAnalysisResult)
        .where(AIAnalysisResult.ai_task_id == task.id)
        .order_by(AIAnalysisResult.id.desc())
    )
    post = db.get(Post, task.post_id)
    serialized["reply"] = serialize_model(reply) if reply else None
    serialized["analysis"] = serialize_model(analysis) if analysis else None
    serialized["post"] = serialize_model(post) if post else None
    return serialized


@router.get("/tasks")
def list_ai_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(AITask).order_by(AITask.created_at.desc())).all()
    return ok([serialize_task(item, db) for item in items], request.state.trace_id)


@router.post("/tasks/{post_id}/analyze")
def analyze_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        result = AIAnalysisService().analyze(db, post_id)
    except AIProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = serialize_task(result["task"], db)
    return ok(payload, request.state.trace_id, "post analyzed")


@router.post("/tasks/{post_id}/generate-reply")
def generate_reply(
    post_id: int,
    payload: ReplyGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = ReplyGenerationService().generate(
            db,
            post_id=post_id,
            strategy=payload.strategy,
            tone=payload.tone,
            variables=payload.variables,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ok(serialize_task(result["task"], db), request.state.trace_id, "reply generated")


@router.post("/tasks/{task_id}/regenerate")
def regenerate_task(
    task_id: int,
    payload: ReplyGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    task = db.get(AITask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    result = ReplyGenerationService().generate(
        db,
        post_id=task.post_id,
        strategy=payload.strategy or task.strategy,
        tone=payload.tone,
        variables=payload.variables,
        task_id=task.id,
    )
    return ok(serialize_task(result["task"], db), request.state.trace_id, "reply regenerated")


@router.post("/tasks/{task_id}/preview-prompt")
def preview_task_prompt(
    task_id: int,
    payload: PromptPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = preview_prompt(
            db,
            task_id=task_id,
            strategy=payload.strategy,
            tone=payload.tone,
            variables=payload.variables,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ok(result, request.state.trace_id, "prompt preview generated")


@router.post("/generate-mock", status_code=status.HTTP_201_CREATED)
def generate_mock(
    payload: MockAIGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    result = ReplyGenerationService().generate(
        db,
        post_id=payload.post_id,
        strategy=payload.strategy,
        tone="supportive",
        variables={"mode": "legacy_mock_endpoint"},
    )
    return ok(serialize_task(result["task"], db), request.state.trace_id, "mock reply generated")


@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(AITask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    reply = db.scalar(
        select(Reply)
        .where(Reply.ai_task_id == task.id)
        .order_by(Reply.version.desc(), Reply.id.desc())
    )
    if not reply:
        raise HTTPException(status_code=409, detail="AI task has no reply")
    task.status = "APPROVED"
    reply.status = "APPROVED"
    post = db.get(Post, task.post_id)
    if post:
        set_post_status(
            db,
            post,
            "APPROVED",
            event_name="ReplyApproved",
            actor="operator",
            detail={"ai_task_id": task.id, "reply_id": reply.id},
        )
        write_audit(
            db,
            action="Approve",
            entity_type="Post",
            entity_uuid=post.uuid,
            actor="operator",
            trace_id=request.state.trace_id,
            detail={"post_id": post.id, "ai_task_id": task.id, "reply_id": reply.id},
        )
    scheduler_task = None
    if get_scheduler_settings(db).get("auto_queue_on_approval"):
        scheduler_task = queue_approved_ai_task(db, ai_task_id=task.id)
    db.commit()
    db.refresh(task)
    result = serialize_task(task, db)
    result["scheduler_task_id"] = scheduler_task.id if scheduler_task else None
    return ok(result, request.state.trace_id, "AI task approved")


@router.post("/tasks/{task_id}/reject")
def reject_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(AITask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    reply = db.scalar(
        select(Reply)
        .where(Reply.ai_task_id == task.id)
        .order_by(Reply.version.desc(), Reply.id.desc())
    )
    task.status = "REJECTED"
    if reply:
        reply.status = "REJECTED"
    post = db.get(Post, task.post_id)
    if post:
        write_audit(
            db,
            action="Reject",
            entity_type="Post",
            entity_uuid=post.uuid,
            actor="operator",
            trace_id=request.state.trace_id,
            detail={"post_id": post.id, "ai_task_id": task.id},
        )
    db.commit()
    db.refresh(task)
    return ok(serialize_task(task, db), request.state.trace_id, "AI task rejected")


@router.put("/replies/{reply_id}")
def update_reply(
    reply_id: int,
    payload: ReplyUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    reply = db.get(Reply, reply_id)
    if not reply:
        raise HTTPException(status_code=404, detail="reply not found")
    reply.content = payload.content
    reply.source = "MANUAL"
    reply.status = "GENERATED"
    db.commit()
    db.refresh(reply)
    return ok(serialize_model(reply), request.state.trace_id, "reply updated")


@router.post("/tasks/batch", status_code=status.HTTP_202_ACCEPTED)
def batch_ai_tasks(
    payload: AIBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    post_ids = list(payload.post_ids)
    if payload.task_ids:
        tasks = db.scalars(select(AITask).where(AITask.id.in_(payload.task_ids))).all()
        post_ids.extend([task.post_id for task in tasks])
    post_ids = list(dict.fromkeys(post_ids))
    if not post_ids:
        raise HTTPException(status_code=400, detail="No tasks or posts selected")
    service = BusinessPipelineService(db, actor="operator", trace_id=request.state.trace_id)
    action = payload.action.upper()
    if action in {"GENERATE", "ANALYZE"}:
        result = service.batch(post_ids, "ANALYZE")
    elif action == "APPROVE":
        result = service.batch(post_ids, "APPROVE")
    elif action == "REJECT":
        result = service.batch(post_ids, "REJECT")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported AI batch action: {payload.action}")
    return ok(result, request.state.trace_id, "AI batch action completed")
