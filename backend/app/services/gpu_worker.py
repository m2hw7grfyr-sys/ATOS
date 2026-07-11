from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Header, HTTPException
from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.config import ensure_gpu_worker_api_key, get_settings, mask_secret
from app.models import GPUGenerationTask, GPUWorkerStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def require_gpu_worker_bearer(authorization: str | None = Header(default=None)) -> None:
    expected = ensure_gpu_worker_api_key()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid bearer token")


class GPUWorkerService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def heartbeat(self, payload: dict[str, Any]) -> GPUWorkerStatus:
        now = utc_now()
        worker_id = str(payload["worker_id"])
        worker = self.db.scalar(
            select(GPUWorkerStatus).where(GPUWorkerStatus.worker_id == worker_id)
        )
        gpu = payload.get("gpu") or {}
        ollama = payload.get("ollama") or {}
        if not worker:
            worker = GPUWorkerStatus(
                worker_id=worker_id,
                worker_name=str(payload.get("worker_name") or worker_id),
                worker_type=str(payload.get("worker_type") or "gpu"),
                created_at=now,
            )
            self.db.add(worker)
            self.db.flush()

        worker.worker_name = str(payload.get("worker_name") or worker.worker_name)
        worker.worker_type = str(payload.get("worker_type") or worker.worker_type or "gpu")
        worker.status = self._normalize_status(str(payload.get("status") or "idle"))
        worker.version = payload.get("version") or worker.version
        worker.last_heartbeat_at = now
        worker.updated_at = now
        worker.gpu_name = gpu.get("name") or worker.gpu_name
        worker.gpu_memory_total_mb = self._int_or_none(gpu.get("memory_total_mb"))
        worker.gpu_memory_free_mb = self._int_or_none(gpu.get("memory_free_mb"))
        worker.ollama_version = (
            ollama.get("version")
            or payload.get("ollama_version")
            or worker.ollama_version
        )
        worker.ollama_reachable = bool(
            ollama.get("reachable", payload.get("ollama_reachable", worker.ollama_reachable))
        )
        worker.model_name = (
            ollama.get("model")
            or ollama.get("model_name")
            or payload.get("model_name")
            or worker.model_name
        )
        worker.current_task_id = payload.get("current_task_id")
        worker.last_error = payload.get("last_error")
        return worker

    def mark_offline_workers(self) -> None:
        threshold = utc_now() - timedelta(seconds=self.settings.gpu_heartbeat_timeout_seconds)
        workers = self.db.scalars(
            select(GPUWorkerStatus).where(
                GPUWorkerStatus.last_heartbeat_at.is_not(None),
                GPUWorkerStatus.last_heartbeat_at < threshold,
                GPUWorkerStatus.status != "offline",
            )
        ).all()
        now = utc_now()
        for worker in workers:
            worker.status = "offline"
            worker.updated_at = now

    def create_task(
        self,
        *,
        prompt: str,
        system_prompt: str | None,
        model: str,
        options: dict[str, Any],
    ) -> GPUGenerationTask:
        now = utc_now()
        task = GPUGenerationTask(
            status="queued",
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            options_json=options or {},
            created_at=now,
            updated_at=now,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def lease_next(
        self, *, worker_id: str, supported_models: list[str] | None
    ) -> GPUGenerationTask | None:
        now = utc_now()
        models = [item for item in (supported_models or []) if item]
        stale = self.db.scalars(
            select(GPUGenerationTask).where(
                GPUGenerationTask.status.in_(["leased", "running"]),
                GPUGenerationTask.lease_expires_at.is_not(None),
                GPUGenerationTask.lease_expires_at < now,
            )
        ).all()
        for task in stale:
            task.status = "queued"
            task.worker_id = None
            task.lease_expires_at = None
            task.updated_at = now

        statement = select(GPUGenerationTask).where(GPUGenerationTask.status == "queued")
        if models:
            statement = statement.where(GPUGenerationTask.model.in_(models))
        task = self.db.scalar(statement.order_by(GPUGenerationTask.created_at.asc()))
        if not task:
            return None

        lease_until = now + timedelta(seconds=self.settings.gpu_task_lease_seconds)
        result = self.db.execute(
            update(GPUGenerationTask)
            .where(
                and_(
                    GPUGenerationTask.id == task.id,
                    GPUGenerationTask.status == "queued",
                )
            )
            .values(
                status="leased",
                worker_id=worker_id,
                lease_expires_at=lease_until,
                attempt_count=GPUGenerationTask.attempt_count + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            return None
        self.db.flush()
        return self.db.get(GPUGenerationTask, task.id)

    def mark_started(self, task_id: int, worker_id: str) -> GPUGenerationTask:
        task = self._worker_task(task_id, worker_id)
        if task.status == "completed":
            return task
        if task.status not in {"leased", "running"}:
            raise ValueError("task is not leased by this worker")
        if self._lease_expired(task):
            raise ValueError("task lease expired")
        now = utc_now()
        task.status = "running"
        task.started_at = task.started_at or now
        task.updated_at = now
        return task

    def complete(
        self,
        task_id: int,
        *,
        worker_id: str,
        result_text: str,
        metrics: dict[str, Any],
    ) -> GPUGenerationTask:
        task = self._worker_task(task_id, worker_id)
        if task.status == "completed":
            return task
        if task.status not in {"leased", "running"}:
            raise ValueError("task is not active")
        if self._lease_expired(task):
            raise ValueError("task lease expired")
        now = utc_now()
        task.status = "completed"
        task.result_text = result_text
        task.metrics_json = metrics or {}
        task.completed_at = now
        task.updated_at = now
        task.lease_expires_at = None
        return task

    def fail(
        self,
        task_id: int,
        *,
        worker_id: str,
        error_type: str,
        error_message: str,
        retryable: bool,
    ) -> GPUGenerationTask:
        task = self._worker_task(task_id, worker_id)
        if task.status == "completed":
            return task
        now = utc_now()
        task.status = "queued" if retryable and task.attempt_count < 3 else "failed"
        task.error_type = error_type
        task.error_message = error_message
        task.retryable = retryable
        task.updated_at = now
        task.lease_expires_at = None
        if task.status == "failed":
            task.completed_at = now
        return task

    def dashboard(self) -> dict[str, Any]:
        self.mark_offline_workers()
        workers = self.db.scalars(
            select(GPUWorkerStatus).order_by(GPUWorkerStatus.updated_at.desc())
        ).all()
        tasks = self.db.scalars(
            select(GPUGenerationTask).order_by(GPUGenerationTask.created_at.desc()).limit(20)
        ).all()
        return {
            "config": {
                "api_key_masked": mask_secret(ensure_gpu_worker_api_key()),
                "heartbeat_timeout_seconds": self.settings.gpu_heartbeat_timeout_seconds,
                "task_lease_seconds": self.settings.gpu_task_lease_seconds,
                "main_bind_host": self.settings.main_bind_host,
                "main_port": self.settings.main_port,
            },
            "workers": [serialize_gpu_worker(worker) for worker in workers],
            "tasks": [serialize_gpu_task(task) for task in tasks],
        }

    def _worker_task(self, task_id: int, worker_id: str) -> GPUGenerationTask:
        task = self.db.get(GPUGenerationTask, task_id)
        if not task:
            raise ValueError("task not found")
        if task.worker_id != worker_id and task.status != "completed":
            raise ValueError("task is not leased by this worker")
        return task

    def _lease_expired(self, task: GPUGenerationTask) -> bool:
        lease = _as_utc(task.lease_expires_at)
        return bool(lease and lease < utc_now())

    def _normalize_status(self, status: str) -> str:
        value = status.lower()
        return value if value in {"offline", "online", "idle", "working", "error"} else "online"

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def serialize_gpu_worker(worker: GPUWorkerStatus) -> dict[str, Any]:
    return {
        "worker_id": worker.worker_id,
        "worker_name": worker.worker_name,
        "worker_type": worker.worker_type,
        "status": worker.status,
        "last_heartbeat_at": _iso(worker.last_heartbeat_at),
        "version": worker.version,
        "gpu_name": worker.gpu_name,
        "gpu_memory_total_mb": worker.gpu_memory_total_mb,
        "gpu_memory_free_mb": worker.gpu_memory_free_mb,
        "ollama_version": worker.ollama_version,
        "ollama_reachable": worker.ollama_reachable,
        "model_name": worker.model_name,
        "current_task_id": worker.current_task_id,
        "last_error": worker.last_error,
        "created_at": _iso(worker.created_at),
        "updated_at": _iso(worker.updated_at),
    }


def serialize_gpu_task(task: GPUGenerationTask, include_prompt: bool = True) -> dict[str, Any]:
    item = {
        "id": task.id,
        "uuid": task.uuid,
        "status": task.status,
        "model": task.model,
        "options": task.options_json or {},
        "result_text": task.result_text,
        "error_message": task.error_message,
        "error_type": task.error_type,
        "retryable": task.retryable,
        "worker_id": task.worker_id,
        "attempt_count": task.attempt_count,
        "lease_expires_at": _iso(task.lease_expires_at),
        "metrics": task.metrics_json or {},
        "created_at": _iso(task.created_at),
        "started_at": _iso(task.started_at),
        "completed_at": _iso(task.completed_at),
        "updated_at": _iso(task.updated_at),
    }
    if include_prompt:
        item["prompt"] = task.prompt
        item["system_prompt"] = task.system_prompt
    return item


def _iso(value: datetime | None) -> str | None:
    return _as_utc(value).isoformat() if value else None
