from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, EngagementStrategy, EngagementTask, StatisticSnapshot
from app.response import ok
from app.schemas import EngagementStrategyCreate, EngagementStrategyUpdate, EngagementTaskCreate
from app.serializers import serialize_model
from app.services.engagement import create_engagement_task, execute_engagement_mock, queue_engagement_task


router = APIRouter(prefix="/engagement", tags=["engagement"])


def serialize_engagement_task(task: EngagementTask, db: Session) -> dict:
    item = serialize_model(task)
    strategy = db.get(EngagementStrategy, task.strategy_id) if task.strategy_id else None
    account = db.get(Account, task.account_id) if task.account_id else None
    item["strategy_name"] = strategy.name if strategy else None
    item["strategy_type"] = strategy.strategy_type if strategy else None
    item["account"] = account.username if account else None
    return item


@router.get("/strategies")
def list_strategies(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(EngagementStrategy).order_by(EngagementStrategy.created_at.desc())).all()
    return ok([serialize_model(item) for item in items], request.state.trace_id)


@router.post("/strategies", status_code=status.HTTP_201_CREATED)
def create_strategy(payload: EngagementStrategyCreate, request: Request, db: Session = Depends(get_db)):
    item = EngagementStrategy(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "strategy created")


@router.put("/strategies/{strategy_id}")
def update_strategy(strategy_id: int, payload: EngagementStrategyUpdate, request: Request, db: Session = Depends(get_db)):
    item = db.get(EngagementStrategy, strategy_id)
    if not item:
        raise HTTPException(status_code=404, detail="strategy not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "strategy updated")


@router.get("/tasks")
def list_tasks(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(EngagementTask).order_by(EngagementTask.created_at.desc())).all()
    return ok([serialize_engagement_task(item, db) for item in items], request.state.trace_id)


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: EngagementTaskCreate, request: Request, db: Session = Depends(get_db)):
    task = create_engagement_task(db, payload.model_dump())
    scheduler_task = queue_engagement_task(db, task)
    db.commit()
    db.refresh(task)
    return ok(
        {"task": serialize_engagement_task(task, db), "scheduler_task_id": scheduler_task.id},
        request.state.trace_id,
        "engagement task queued",
    )


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(EngagementTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    task.status = "CANCELLED"
    db.commit()
    return ok(serialize_engagement_task(task, db), request.state.trace_id, "task cancelled")


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(EngagementTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    task.status = "QUEUED"
    task.error_code = None
    task.error_message = None
    queue_engagement_task(db, task)
    db.commit()
    return ok(serialize_engagement_task(task, db), request.state.trace_id, "task retried")


@router.post("/tasks/{task_id}/run-mock")
def run_task_mock(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(EngagementTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    execute_engagement_mock(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_engagement_task(task, db), request.state.trace_id, "engagement mock completed")


@router.get("/statistics")
def engagement_statistics(request: Request, db: Session = Depends(get_db)):
    stats = db.scalars(
        select(StatisticSnapshot).where(
            StatisticSnapshot.metric.in_(
                [
                    "browse_count",
                    "like_count",
                    "visit_profile_count",
                    "engagement_success_rate",
                    "engagement_failure_rate",
                    "warmup_before_reply_count",
                ]
            )
        )
    ).all()
    return ok([serialize_model(item) for item in stats], request.state.trace_id)
