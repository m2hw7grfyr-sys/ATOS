from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import ExecutionTask, WorkerLog, WorkerNode
from app.response import ok
from app.serializers import serialize_model
from app.services.remote_worker import RemoteWorkerService, require_worker_token, utc_now


router = APIRouter(tags=["workers"])


def serialize_worker(worker: WorkerNode, db: Session) -> dict:
    item = serialize_model(worker)
    item["worker_id"] = worker.name
    item["capabilities"] = worker.capabilities or worker.capability or {}
    item["running_tasks"] = db.scalar(
        select(func.count()).select_from(ExecutionTask).where(
            ExecutionTask.worker_node_id == worker.id,
            ExecutionTask.status.in_(["CLAIMED", "RUNNING", "WAITING_MANUAL"]),
        )
    ) or 0
    return item


@router.get("/worker/health")
def worker_health(request: Request, db: Session = Depends(get_db), _: None = Depends(require_worker_token)):
    settings = get_settings()
    return ok(
        {
            "status": "HEALTHY",
            "version": settings.app_version,
            "worker_id": "server-local",
            "runtime_status": "READY",
            "last_heartbeat": utc_now().isoformat(),
        },
        request.state.trace_id,
    )


@router.post("/workers/register")
def register_worker(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    worker = RemoteWorkerService(db).register(payload, request)
    db.commit()
    db.refresh(worker)
    return ok(serialize_worker(worker, db), request.state.trace_id, "worker registered")


@router.post("/workers/heartbeat")
def heartbeat_worker(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    service = RemoteWorkerService(db)
    worker = service.heartbeat(payload, request)
    service.mark_stale_workers()
    db.commit()
    db.refresh(worker)
    return ok(serialize_worker(worker, db), request.state.trace_id, "worker heartbeat accepted")


@router.get("/workers")
def list_workers(request: Request, db: Session = Depends(get_db), _: None = Depends(require_worker_token)):
    service = RemoteWorkerService(db)
    service.mark_stale_workers()
    db.commit()
    workers = db.scalars(select(WorkerNode).order_by(WorkerNode.updated_at.desc())).all()
    return ok([serialize_worker(worker, db) for worker in workers], request.state.trace_id)


@router.get("/workers/{worker_id}")
def get_worker(
    worker_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    worker = db.get(WorkerNode, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="worker not found")
    return ok(serialize_worker(worker, db), request.state.trace_id)


@router.post("/workers/{worker_id}/restart")
def restart_worker(
    worker_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    try:
        worker = RemoteWorkerService(db).restart(worker_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(worker)
    return ok(serialize_worker(worker, db), request.state.trace_id, "worker restart requested")


@router.get("/workers/{worker_id}/logs")
def get_worker_logs(
    worker_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    worker = db.get(WorkerNode, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="worker not found")
    logs = db.scalars(
        select(WorkerLog)
        .where(WorkerLog.worker_node_id == worker.id)
        .order_by(WorkerLog.created_at.desc())
        .limit(200)
    ).all()
    return ok([serialize_model(log) for log in logs], request.state.trace_id)
