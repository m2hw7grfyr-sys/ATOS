from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import ensure_gpu_worker_api_key
from app.database import get_db
from app.response import ok
from app.schemas import (
    GPUGenerationTaskCreate,
    GPUWorkerHeartbeat,
    GPUWorkerLeaseRequest,
    GPUWorkerTaskComplete,
    GPUWorkerTaskFailed,
    GPUWorkerTaskStarted,
)
from app.services.gpu_worker import (
    GPUWorkerService,
    require_gpu_worker_bearer,
    serialize_gpu_task,
    serialize_gpu_worker,
    utc_now,
)


router = APIRouter(prefix="/api/gpu-worker", tags=["gpu-worker"])


@router.post("/heartbeat")
def gpu_worker_heartbeat(
    payload: GPUWorkerHeartbeat,
    db: Session = Depends(get_db),
    _: None = Depends(require_gpu_worker_bearer),
):
    service = GPUWorkerService(db)
    worker = service.heartbeat(payload.model_dump())
    db.commit()
    db.refresh(worker)
    return {
        "ok": True,
        "server_time": utc_now().astimezone(timezone.utc).isoformat(),
        "heartbeat_interval_seconds": 10,
        "worker": serialize_gpu_worker(worker),
    }


@router.post("/tasks/lease")
def lease_gpu_task(
    payload: GPUWorkerLeaseRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_gpu_worker_bearer),
):
    service = GPUWorkerService(db)
    task = service.lease_next(
        worker_id=payload.worker_id,
        supported_models=payload.supported_models,
    )
    db.commit()
    if not task:
        return {"task": None, "retry_after_seconds": 5}
    db.refresh(task)
    return {
        "task": {
            "id": task.id,
            "prompt": task.prompt,
            "system_prompt": task.system_prompt,
            "model": task.model,
            "options": task.options_json or {},
        },
        "lease_seconds": service.settings.gpu_task_lease_seconds,
    }


@router.post("/tasks/{task_id}/started")
def mark_gpu_task_started(
    task_id: int,
    payload: GPUWorkerTaskStarted,
    db: Session = Depends(get_db),
    _: None = Depends(require_gpu_worker_bearer),
):
    try:
        task = GPUWorkerService(db).mark_started(task_id, payload.worker_id)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "lease" in str(exc) else 404, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return {"ok": True, "task": serialize_gpu_task(task, include_prompt=False)}


@router.post("/tasks/{task_id}/complete")
def complete_gpu_task(
    task_id: int,
    payload: GPUWorkerTaskComplete,
    db: Session = Depends(get_db),
    _: None = Depends(require_gpu_worker_bearer),
):
    try:
        task = GPUWorkerService(db).complete(
            task_id,
            worker_id=payload.worker_id,
            result_text=payload.result_text,
            metrics=payload.metrics,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409 if "lease" in str(exc) else 404, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return {"ok": True, "task": serialize_gpu_task(task)}


@router.post("/tasks/{task_id}/failed")
def fail_gpu_task(
    task_id: int,
    payload: GPUWorkerTaskFailed,
    db: Session = Depends(get_db),
    _: None = Depends(require_gpu_worker_bearer),
):
    try:
        task = GPUWorkerService(db).fail(
            task_id,
            worker_id=payload.worker_id,
            error_type=payload.error_type,
            error_message=payload.error_message,
            retryable=payload.retryable,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return {"ok": True, "task": serialize_gpu_task(task)}


@router.get("/dashboard")
def gpu_worker_dashboard(request: Request, db: Session = Depends(get_db)):
    service = GPUWorkerService(db)
    data = service.dashboard()
    db.commit()
    return ok(data, request.state.trace_id)


@router.post("/tasks")
def create_gpu_generation_task(
    payload: GPUGenerationTaskCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    task = GPUWorkerService(db).create_task(
        prompt=payload.prompt,
        system_prompt=payload.system_prompt,
        model=payload.model,
        options=payload.options,
    )
    db.commit()
    db.refresh(task)
    return ok(serialize_gpu_task(task), request.state.trace_id, "gpu generation task queued")


@router.get("/config")
def gpu_worker_config(request: Request):
    key = ensure_gpu_worker_api_key()
    return ok(
        {
            "api_key_masked": f"{key[:8]}...{key[-4:]}",
            "copy_available": True,
            "api_key": key,
        },
        request.state.trace_id,
    )
