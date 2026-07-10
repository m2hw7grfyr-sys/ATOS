from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import WorkerLog, WorkerNode


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_worker_token(x_worker_token: Optional[str] = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.worker_api_token
    if not expected:
        raise HTTPException(status_code=503, detail="WORKER_API_TOKEN is not configured")
    if x_worker_token != expected:
        raise HTTPException(status_code=401, detail="invalid worker token")


class RemoteWorkerService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def register(self, payload: dict[str, Any], request: Request | None = None) -> WorkerNode:
        name = str(payload.get("name") or payload.get("worker_id") or socket.gethostname())
        worker = self.db.scalar(select(WorkerNode).where(WorkerNode.name == name))
        now = utc_now()
        capabilities = payload.get("capabilities") or payload.get("capability") or {}
        if not worker:
            worker = WorkerNode(
                name=name,
                status="ONLINE",
                host=str(payload.get("host") or payload.get("hostname") or ""),
                hostname=str(payload.get("hostname") or payload.get("host") or ""),
                os=str(payload.get("os") or ""),
                ip=str(payload.get("ip") or self._request_ip(request) or ""),
                version=str(payload.get("version") or "remote"),
                capability=capabilities,
                capabilities=capabilities,
                runtime_status=str(payload.get("runtime_status") or "READY"),
                token_version=self.settings.worker_token_version,
                last_seen=now,
                last_heartbeat=now,
            )
            self.db.add(worker)
            self.db.flush()
        else:
            worker.status = "ONLINE"
            worker.host = str(payload.get("host") or worker.host or "")
            worker.hostname = str(payload.get("hostname") or payload.get("host") or worker.hostname or "")
            worker.os = str(payload.get("os") or worker.os or "")
            worker.ip = str(payload.get("ip") or self._request_ip(request) or worker.ip or "")
            worker.version = str(payload.get("version") or worker.version or "remote")
            worker.capability = capabilities or worker.capability or {}
            worker.capabilities = capabilities or worker.capabilities or worker.capability or {}
            worker.runtime_status = str(payload.get("runtime_status") or worker.runtime_status or "READY")
            worker.token_version = self.settings.worker_token_version
            worker.last_seen = now
            worker.last_heartbeat = now
        self.log(worker, "application", "INFO", "Worker registered", {"payload_keys": sorted(payload.keys())})
        return worker

    def heartbeat(self, payload: dict[str, Any], request: Request | None = None) -> WorkerNode:
        worker_id = payload.get("worker_id") or payload.get("id") or payload.get("name")
        worker = self._find_worker(worker_id)
        if not worker:
            worker = self.register(payload, request)
        now = utc_now()
        worker.status = "ONLINE"
        worker.ip = str(payload.get("ip") or self._request_ip(request) or worker.ip or "")
        worker.cpu = self._float_or_none(payload.get("cpu"))
        worker.memory = self._float_or_none(payload.get("memory"))
        worker.gpu = self._float_or_none(payload.get("gpu"))
        worker.runtime_status = str(payload.get("runtime_status") or worker.runtime_status or "READY")
        worker.capabilities = payload.get("capabilities") or worker.capabilities or worker.capability or {}
        worker.capability = worker.capabilities
        worker.last_seen = now
        worker.last_heartbeat = now
        self.log(worker, "application", "INFO", "Worker heartbeat", {"runtime_status": worker.runtime_status})
        return worker

    def mark_stale_workers(self) -> None:
        threshold = utc_now() - timedelta(seconds=self.settings.worker_heartbeat_timeout_seconds)
        workers = self.db.scalars(
            select(WorkerNode).where(
                WorkerNode.status == "ONLINE",
                WorkerNode.last_seen.is_not(None),
                WorkerNode.last_seen < threshold,
            )
        ).all()
        for worker in workers:
            worker.status = "OFFLINE"
            worker.runtime_status = "OFFLINE"
            self.log(worker, "application", "WARNING", "Worker marked offline by heartbeat timeout")

    def restart(self, worker_id: int) -> WorkerNode:
        worker = self.db.get(WorkerNode, worker_id)
        if not worker:
            raise ValueError("worker not found")
        worker.runtime_status = "RESTART_REQUESTED"
        self.log(worker, "application", "WARNING", "Restart requested by server")
        return worker

    def log(
        self,
        worker: WorkerNode | None,
        log_type: str,
        level: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerLog:
        item = WorkerLog(
            worker_node_id=worker.id if worker else None,
            worker_id=worker.name if worker else None,
            log_type=log_type,
            level=level.upper(),
            message=message,
            metadata_json=metadata or {},
        )
        self.db.add(item)
        self.db.flush()
        return item

    def _find_worker(self, worker_id: Any) -> WorkerNode | None:
        if worker_id is None:
            return None
        if isinstance(worker_id, int) or str(worker_id).isdigit():
            worker = self.db.get(WorkerNode, int(worker_id))
            if worker:
                return worker
        return self.db.scalar(select(WorkerNode).where(WorkerNode.name == str(worker_id)))

    def _request_ip(self, request: Request | None) -> str | None:
        if not request or not request.client:
            return None
        return request.headers.get("CF-Connecting-IP") or request.client.host

    def _float_or_none(self, value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
