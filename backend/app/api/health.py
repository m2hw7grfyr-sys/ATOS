from __future__ import annotations

import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AIGenerationLog, ExecutionQueue, ExecutionTask, SubmissionTask, SystemAlert, WorkerNode
from app.response import ok
from app.services.submission_runtime import SubmissionRuntime


router = APIRouter(tags=["health"])
STARTED_AT = time.monotonic()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def uptime_seconds() -> int:
    return int(time.monotonic() - STARTED_AT)


def base_payload(status: str = "HEALTHY", **extra):
    settings = get_settings()
    return {
        "status": status,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime": uptime_seconds(),
        "timestamp": timestamp(),
        **extra,
    }


def database_status(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "HEALTHY"}
    except Exception as exc:  # pragma: no cover - defensive health path
        return {"status": "ERROR", "message": str(exc)}


def redis_status() -> dict:
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return {"status": "HEALTHY", "host": host, "port": port}
    except Exception as exc:
        return {"status": "ERROR", "host": host, "port": port, "message": str(exc)}


def worker_status(db: Session) -> dict:
    online = db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == "ONLINE")) or 0
    offline = db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == "OFFLINE")) or 0
    status = "HEALTHY" if online > 0 else "WARNING"
    return {"status": status, "online": online, "offline": offline}


def scheduler_status(db: Session) -> dict:
    queued = db.scalar(select(func.count()).select_from(ExecutionQueue).where(ExecutionQueue.status.in_(["QUEUED", "RETRY_PENDING"]))) or 0
    return {"status": "HEALTHY", "queue_length": queued}


def ai_runtime_status(db: Session) -> dict:
    errors = db.scalar(select(func.count()).select_from(AIGenerationLog).where(AIGenerationLog.status == "ERROR")) or 0
    return {"status": "HEALTHY" if errors == 0 else "WARNING", "error_count": errors}


def browser_runtime_status(db: Session) -> dict:
    running = db.scalar(select(func.count()).select_from(ExecutionTask).where(ExecutionTask.status.in_(["RUNNING", "WAITING_MANUAL"]))) or 0
    return {"status": "HEALTHY", "running_tasks": running}


def production_security_status() -> dict:
    settings = get_settings()
    checks = {
        "debug_disabled": not settings.debug,
        "cors_restricted": "*" not in settings.cors_origin_list and bool(settings.cors_origin_list),
        "worker_token_configured": bool(settings.worker_api_token) if settings.is_production else True,
        "cookie_secure": settings.cookie_secure if settings.is_production else True,
        "admin_default_password_changed": settings.admin_default_password_changed if settings.is_production else True,
    }
    failed = [key for key, value in checks.items() if not value]
    return {"status": "HEALTHY" if not failed else "WARNING", "checks": checks, "failed": failed}


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)):
    dependencies = {
        "database": database_status(db),
        "redis": redis_status(),
        "worker": worker_status(db),
        "scheduler": scheduler_status(db),
        "ai_runtime": ai_runtime_status(db),
        "browser_runtime": browser_runtime_status(db),
        "security": production_security_status(),
    }
    status = "HEALTHY" if all(item["status"] in {"HEALTHY", "WARNING"} for item in dependencies.values()) else "ERROR"
    return ok(base_payload(status=status, dependencies=dependencies), request.state.trace_id)


@router.get("/health/backend")
def health_backend(request: Request):
    return ok(base_payload(status="HEALTHY"), request.state.trace_id)


@router.get("/health/database")
def health_database(request: Request, db: Session = Depends(get_db)):
    return ok(base_payload(**database_status(db)), request.state.trace_id)


@router.get("/health/redis")
def health_redis(request: Request):
    return ok(base_payload(**redis_status()), request.state.trace_id)


@router.get("/health/worker")
def health_worker(request: Request, db: Session = Depends(get_db)):
    return ok(base_payload(**worker_status(db)), request.state.trace_id)


@router.get("/health/scheduler")
def health_scheduler(request: Request, db: Session = Depends(get_db)):
    return ok(base_payload(**scheduler_status(db)), request.state.trace_id)


@router.get("/health/ai-runtime")
def health_ai_runtime(request: Request, db: Session = Depends(get_db)):
    return ok(base_payload(**ai_runtime_status(db)), request.state.trace_id)


@router.get("/health/browser-runtime")
def health_browser_runtime(request: Request, db: Session = Depends(get_db)):
    return ok(base_payload(**browser_runtime_status(db)), request.state.trace_id)


@router.get("/ready")
def ready(request: Request, db: Session = Depends(get_db)):
    dependencies = {"database": database_status(db), "redis": redis_status()}
    status = "READY" if dependencies["database"]["status"] == "HEALTHY" else "NOT_READY"
    return ok(base_payload(status=status, dependencies=dependencies), request.state.trace_id)


@router.get("/live")
def live(request: Request):
    return ok(base_payload(status="LIVE"), request.state.trace_id)


@router.get("/metrics")
def metrics(request: Request, db: Session = Depends(get_db)):
    queued = db.scalar(select(func.count()).select_from(ExecutionQueue).where(ExecutionQueue.status.in_(["QUEUED", "RETRY_PENDING"]))) or 0
    online = db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == "ONLINE")) or 0
    offline = db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == "OFFLINE")) or 0
    execution_total = db.scalar(select(func.count()).select_from(ExecutionTask)) or 0
    execution_success = db.scalar(select(func.count()).select_from(ExecutionTask).where(ExecutionTask.status == "SUCCESS")) or 0
    submission_total = db.scalar(select(func.count()).select_from(SubmissionTask)) or 0
    submission_success = db.scalar(select(func.count()).select_from(SubmissionTask).where(SubmissionTask.status.in_(["VERIFIED", "COMPLETED"]))) or 0
    ai_errors = db.scalar(select(func.count()).select_from(AIGenerationLog).where(AIGenerationLog.status == "ERROR")) or 0
    submission_dashboard = SubmissionRuntime(db).dashboard_counts()
    alerts = db.scalar(select(func.count()).select_from(SystemAlert).where(SystemAlert.status == "OPEN")) or 0
    redis = redis_status()
    database = database_status(db)
    return ok(
        {
            "task_queue_length": queued,
            "worker_online_count": online,
            "worker_offline_count": offline,
            "execution_success_rate": round((execution_success / max(execution_total, 1)) * 100, 2),
            "submission_success_rate": round((submission_success / max(submission_total, 1)) * 100, 2),
            "ai_provider_error_count": ai_errors,
            "auto_assisted_enabled_count": submission_dashboard.get("auto_assisted_submitting", 0),
            "database_status": database["status"],
            "redis_status": redis["status"],
            "open_alert_count": alerts,
            "timestamp": timestamp(),
        },
        request.state.trace_id,
    )
