from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, ExecutionLog, ExecutionTask, ReplayFile, SchedulerTask, TGEProfile
from app.response import ok
from app.serializers import serialize_model
from app.services.execution import run_precheck, set_execution_status


router = APIRouter(prefix="/execution", tags=["execution"])


def serialize_execution_task(task: ExecutionTask, db: Session) -> dict:
    item = serialize_model(task)
    scheduler_task = db.get(SchedulerTask, task.scheduler_task_id) if task.scheduler_task_id else None
    account = db.get(Account, task.account_id) if task.account_id else None
    profile = db.get(TGEProfile, task.tge_profile_id) if task.tge_profile_id else None
    item["task_id"] = task.id
    item["scheduler_status"] = scheduler_task.status if scheduler_task else None
    item["execution_status"] = task.status
    item["account"] = account.username if account else None
    item["tge_environment_id"] = (
        profile.tge_environment_id or profile.environment_id if profile else None
    )
    return item


@router.get("/tasks")
def list_execution_tasks(request: Request, db: Session = Depends(get_db)):
    tasks = db.scalars(select(ExecutionTask).order_by(ExecutionTask.created_at.desc())).all()
    return ok([serialize_execution_task(task, db) for task in tasks], request.state.trace_id)


@router.get("/tasks/{task_id}")
def get_execution_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    return ok(serialize_execution_task(task, db), request.state.trace_id)


@router.post("/tasks/{task_id}/precheck")
def precheck_execution_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    run_precheck(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "precheck completed")


@router.post("/tasks/{task_id}/mark-success")
def mark_success(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    set_execution_status(db, task, "SUCCESS", "MARK_SUCCESS", message="Marked success manually")
    db.commit()
    return ok(serialize_execution_task(task, db), request.state.trace_id, "execution marked success")


@router.post("/tasks/{task_id}/mark-failed")
def mark_failed(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    set_execution_status(db, task, "FAILED", "MARK_FAILED", error_code="MANUAL_FAILED", error_message="Marked failed manually")
    db.commit()
    return ok(serialize_execution_task(task, db), request.state.trace_id, "execution marked failed")


@router.get("/tasks/{task_id}/replay")
def get_replay(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    replay = db.scalar(select(ReplayFile).where(ReplayFile.execution_task_id == task.id))
    return ok(serialize_model(replay) if replay else None, request.state.trace_id)


@router.get("/tasks/{task_id}/logs")
def get_execution_logs(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    logs = db.scalars(
        select(ExecutionLog).where(ExecutionLog.execution_task_id == task.id).order_by(ExecutionLog.created_at.desc())
    ).all()
    return ok([serialize_model(log) for log in logs], request.state.trace_id)
