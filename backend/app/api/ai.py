from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AITask, Post, Reply, SystemSetting
from app.response import ok
from app.schemas import MockAIGenerateRequest
from app.serializers import serialize_model


router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/tasks")
def list_ai_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(AITask).order_by(AITask.created_at.desc())).all()
    replies = {
        reply.ai_task_id: reply
        for reply in db.scalars(select(Reply).where(Reply.ai_task_id.is_not(None))).all()
    }
    result = []
    for item in items:
        serialized = serialize_model(item)
        reply = replies.get(item.id)
        serialized["reply"] = serialize_model(reply) if reply else None
        result.append(serialized)
    return ok(result, request.state.trace_id)


@router.post("/generate-mock", status_code=status.HTTP_201_CREATED)
def generate_mock(
    payload: MockAIGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    post = db.get(Post, payload.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    provider_setting = db.scalar(
        select(SystemSetting).where(SystemSetting.key == "ai.default_provider")
    )
    provider_config = provider_setting.value if provider_setting else {}
    provider = provider_config.get("provider", "mock")
    model = provider_config.get("model", "mock-v0.1")
    task = AITask(
        post_id=post.id,
        provider=f"mock:{provider}",
        model=model,
        strategy=payload.strategy.upper(),
        commercial_score=68,
        risk_score=12,
        result={
            "intent": ["QUESTION"],
            "confidence": 0.84,
            "mock": True,
            "note": "Generated locally without an external LLM call.",
        },
        status="REVIEWING",
    )
    db.add(task)
    db.flush()
    reply = Reply(
        post_id=post.id,
        ai_task_id=task.id,
        content=(
            f"Mock draft for review: {post.title}. "
            "A useful first step is to define one small, repeatable action and evaluate it weekly."
        ),
        source="MOCK_PROVIDER",
        status="GENERATED",
    )
    db.add(reply)
    post.status = "AI_REVIEW"
    db.commit()
    db.refresh(task)
    result = serialize_model(task)
    result["reply"] = serialize_model(reply)
    return ok(result, request.state.trace_id, "mock reply generated")


@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(AITask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="AI task not found")
    reply = db.scalar(select(Reply).where(Reply.ai_task_id == task.id))
    if not reply:
        raise HTTPException(status_code=409, detail="AI task has no reply")
    task.status = "APPROVED"
    reply.status = "APPROVED"
    db.commit()
    db.refresh(task)
    result = serialize_model(task)
    result["reply"] = serialize_model(reply)
    return ok(result, request.state.trace_id, "AI task approved")
