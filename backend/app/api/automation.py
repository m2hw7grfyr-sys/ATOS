from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExecutionQueue, ExecutionTask, RuntimeMetric, SystemAlert, TaskLock, WorkerLog, WorkerNode
from app.response import ok
from app.serializers import serialize_model
from app.services.automation_runtime import AutomationRuntime


router = APIRouter(prefix="/automation", tags=["automation"])


def serialize_worker(worker: WorkerNode) -> dict:
    item = serialize_model(worker)
    item["worker_id"] = worker.name
    item["capabilities"] = worker.capabilities or worker.capability or {}
    return item


def serialize_task(task: ExecutionTask) -> dict:
    item = serialize_model(task)
    item["task_id"] = task.id
    item["claimed_by_worker"] = task.claimed_by_worker
    return item


@router.get("/runtime")
def runtime_status(request: Request, db: Session = Depends(get_db)):
    runtime = AutomationRuntime(db)
    data = runtime.runtime_status()
    db.commit()
    return ok(data, request.state.trace_id)


@router.get("/workers")
def list_workers(request: Request, db: Session = Depends(get_db)):
    runtime = AutomationRuntime(db)
    runtime.mark_stale_workers()
    db.commit()
    workers = db.scalars(select(WorkerNode).order_by(WorkerNode.priority.asc(), WorkerNode.updated_at.desc())).all()
    return ok([serialize_worker(worker) for worker in workers], request.state.trace_id)


@router.post("/workers/register")
def register_worker(payload: dict, request: Request, db: Session = Depends(get_db)):
    worker = AutomationRuntime(db).register_worker(payload)
    db.commit()
    db.refresh(worker)
    return ok(serialize_worker(worker), request.state.trace_id, "worker registered")


@router.post("/workers/heartbeat")
def heartbeat_worker(payload: dict, request: Request, db: Session = Depends(get_db)):
    runtime = AutomationRuntime(db)
    worker = runtime.heartbeat(payload)
    runtime.mark_stale_workers()
    db.commit()
    db.refresh(worker)
    return ok(serialize_worker(worker), request.state.trace_id, "heartbeat accepted")


@router.post("/claim")
def claim_task(payload: dict, request: Request, db: Session = Depends(get_db)):
    task = AutomationRuntime(db).claim_next(payload.get("worker_id"))
    db.commit()
    if task:
        db.refresh(task)
    return ok(serialize_task(task) if task else None, request.state.trace_id, "claim completed")


@router.post("/tasks/{task_id}/start")
def start_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    AutomationRuntime(db).start_task(task)
    db.commit()
    db.refresh(task)
    return ok(serialize_task(task), request.state.trace_id, "task started")


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    success = bool(payload.get("success", True))
    AutomationRuntime(db).complete_task(task, success=success, message=payload.get("message"))
    db.commit()
    db.refresh(task)
    return ok(serialize_task(task), request.state.trace_id, "task completed")


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    AutomationRuntime(db).schedule_retry(task, payload.get("reason"))
    db.commit()
    db.refresh(task)
    return ok(serialize_task(task), request.state.trace_id, "retry scheduled")


@router.post("/recover")
def recover(request: Request, db: Session = Depends(get_db)):
    runtime = AutomationRuntime(db)
    stale = runtime.mark_stale_workers()
    db.commit()
    return ok({"stale_workers": [serialize_worker(worker) for worker in stale]}, request.state.trace_id, "recovery checked")


@router.get("/queue")
def list_queue(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(ExecutionQueue).order_by(ExecutionQueue.queued_at.desc())).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)


@router.get("/locks")
def list_locks(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(TaskLock).order_by(TaskLock.created_at.desc()).limit(200)).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)


@router.get("/metrics")
def runtime_metrics(request: Request, db: Session = Depends(get_db)):
    runtime = AutomationRuntime(db)
    current = runtime.metrics()
    rows = db.scalars(select(RuntimeMetric).order_by(RuntimeMetric.created_at.desc()).limit(100)).all()
    db.commit()
    return ok({"current": current, "history": [serialize_model(row) for row in rows]}, request.state.trace_id)


@router.get("/alerts")
def list_alerts(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(SystemAlert).order_by(SystemAlert.created_at.desc()).limit(100)).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)


@router.get("/logs")
def list_automation_logs(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(WorkerLog)
        .where(WorkerLog.log_type == "automation")
        .order_by(WorkerLog.created_at.desc())
        .limit(200)
    ).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)
