from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExecutionQueue, ExecutionTask, RuntimeMetric, SystemAlert, TaskLock, WorkerLog, WorkerNode
from app.services.execution import execution_log, set_execution_status


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PRIORITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 10,
    "NORMAL": 50,
    "MEDIUM": 50,
    "LOW": 100,
}


class AutomationRuntime:
    def __init__(self, db: Session):
        self.db = db

    def register_worker(self, payload: dict[str, Any]) -> WorkerNode:
        name = str(payload.get("name") or payload.get("worker_id") or socket.gethostname())
        worker = self.db.scalar(select(WorkerNode).where(WorkerNode.name == name))
        capabilities = self._normalize_capabilities(payload.get("capabilities") or payload.get("capability") or {})
        now = utc_now()
        if not worker:
            worker = WorkerNode(
                name=name,
                status="ONLINE",
                host=str(payload.get("host") or payload.get("hostname") or ""),
                hostname=str(payload.get("hostname") or payload.get("host") or ""),
                os=str(payload.get("os") or ""),
                ip=str(payload.get("ip") or ""),
                version=str(payload.get("version") or "automation"),
                worker_type=str(payload.get("worker_type") or "REMOTE"),
                capability=capabilities,
                capabilities=capabilities,
                max_concurrent_tasks=int(payload.get("max_concurrent_tasks") or 1),
                current_tasks=0,
                priority=int(payload.get("priority") or 100),
                region=payload.get("region"),
                runtime_status=str(payload.get("runtime_status") or "READY"),
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
            worker.ip = str(payload.get("ip") or worker.ip or "")
            worker.version = str(payload.get("version") or worker.version or "automation")
            worker.worker_type = str(payload.get("worker_type") or worker.worker_type or "REMOTE")
            worker.capability = capabilities or worker.capability or {}
            worker.capabilities = capabilities or worker.capabilities or worker.capability or {}
            worker.max_concurrent_tasks = int(payload.get("max_concurrent_tasks") or worker.max_concurrent_tasks or 1)
            worker.priority = int(payload.get("priority") or worker.priority or 100)
            worker.region = payload.get("region") or worker.region
            worker.runtime_status = str(payload.get("runtime_status") or worker.runtime_status or "READY")
            worker.last_seen = now
            worker.last_heartbeat = now
        self.update_worker_load(worker)
        self.log(worker, None, "INFO", "automation", "Worker registered", {"capabilities": worker.capabilities})
        return worker

    def heartbeat(self, payload: dict[str, Any]) -> WorkerNode:
        worker = self.find_worker(payload.get("worker_id") or payload.get("id") or payload.get("name"))
        if not worker:
            worker = self.register_worker(payload)
        worker.status = "ONLINE"
        worker.cpu = self._float_or_none(payload.get("cpu"))
        worker.memory = self._float_or_none(payload.get("memory"))
        worker.gpu = self._float_or_none(payload.get("gpu"))
        worker.runtime_status = str(payload.get("runtime_status") or worker.runtime_status or "READY")
        worker.capabilities = self._normalize_capabilities(payload.get("capabilities") or worker.capabilities or worker.capability or {})
        worker.capability = worker.capabilities
        worker.last_seen = utc_now()
        worker.last_heartbeat = worker.last_seen
        self.update_worker_load(worker)
        self.calculate_worker_health(worker)
        self.log(worker, None, "INFO", "heartbeat", "Worker heartbeat", {"runtime_status": worker.runtime_status})
        return worker

    def mark_stale_workers(self, timeout_seconds: int = 90) -> list[WorkerNode]:
        threshold = utc_now() - timedelta(seconds=timeout_seconds)
        stale = self.db.scalars(
            select(WorkerNode).where(
                WorkerNode.status == "ONLINE",
                WorkerNode.last_heartbeat.is_not(None),
                WorkerNode.last_heartbeat < threshold,
            )
        ).all()
        for worker in stale:
            worker.status = "OFFLINE"
            worker.runtime_status = "OFFLINE"
            worker.health_score = min(float(worker.health_score or 100), 40)
            self.log(worker, None, "WARNING", "monitor", "Worker marked offline by heartbeat timeout")
            self.create_alert(
                "WORKER_OFFLINE",
                f"Worker {worker.name} missed heartbeat for {timeout_seconds} seconds.",
                severity="ERROR",
                metadata={"worker_id": worker.id},
            )
            self.recover_worker_tasks(worker)
        return stale

    def claim_next(self, worker_id: int | str | None = None) -> ExecutionTask | None:
        worker = self.find_worker(worker_id) if worker_id else self.best_worker()
        if not worker:
            return None
        self.update_worker_load(worker)
        if worker.current_tasks >= worker.max_concurrent_tasks:
            return None

        now = utc_now()
        candidates = self.db.scalars(
            select(ExecutionQueue).where(
                ExecutionQueue.status.in_(["QUEUED", "RETRY_PENDING"]),
            )
        ).all()
        eligible = []
        for queue in candidates:
            task = self.db.get(ExecutionTask, queue.execution_task_id)
            if not task or task.status in {"CANCELLED", "SUCCESS"}:
                continue
            if task.next_retry_at and task.next_retry_at > now:
                continue
            if not self.worker_supports(worker, queue.required_capability or self.required_capability(task)):
                continue
            eligible.append(queue)
        eligible.sort(key=lambda item: (PRIORITY_ORDER.get((item.priority or "NORMAL").upper(), 50), item.queued_at))
        if not eligible:
            return None

        queue = eligible[0]
        task = self.db.get(ExecutionTask, queue.execution_task_id)
        if not task:
            queue.status = "FAILED"
            queue.error_message = "Execution task missing"
            return None
        lock = self.acquire_lock(task, worker)
        if not lock:
            return None

        old_status = task.status
        queue.status = "CLAIMED"
        queue.worker_node_id = worker.id
        queue.claimed_at = now
        queue.lock_uuid = lock.uuid
        queue.lock_expires_at = lock.expires_at
        queue.required_capability = queue.required_capability or self.required_capability(task)
        task.status = "CLAIMED"
        task.queue_status = "CLAIMED"
        task.worker_node_id = worker.id
        task.claimed_by_worker = worker.name
        task.claimed_at = now
        task.last_heartbeat_at = now
        task.lock_uuid = lock.uuid
        self.update_worker_load(worker)
        execution_log(
            self.db,
            task,
            "TASK_CLAIMED",
            old_status=old_status,
            new_status="CLAIMED",
            message=f"Claimed by {worker.name}",
            metadata={"lock_uuid": lock.uuid, "capability": queue.required_capability},
        )
        self.log(worker, task, "INFO", "claim", "Task claimed", {"execution_task_id": task.id})
        return task

    def start_task(self, task: ExecutionTask) -> ExecutionTask:
        queue = self.queue_for_task(task)
        if queue:
            queue.status = "RUNNING"
            queue.started_at = utc_now()
        task.status = "RUNNING"
        task.queue_status = "RUNNING"
        task.started_at = task.started_at or utc_now()
        task.last_heartbeat_at = utc_now()
        execution_log(self.db, task, "TASK_RUNNING", old_status="CLAIMED", new_status="RUNNING")
        return task

    def complete_task(self, task: ExecutionTask, *, success: bool, message: str | None = None) -> ExecutionTask:
        queue = self.queue_for_task(task)
        status = "SUCCESS" if success else "FAILED"
        if queue:
            queue.status = status
            queue.finished_at = utc_now()
            queue.error_message = None if success else message
        set_execution_status(
            self.db,
            task,
            status,
            "EXECUTION_SUCCESS" if success else "EXECUTION_FAILED",
            message=message,
            error_code=None if success else "WORKER_FAILED",
            error_message=None if success else message,
        )
        task.queue_status = status
        self.release_lock(task)
        if task.worker_node_id:
            worker = self.db.get(WorkerNode, task.worker_node_id)
            if worker:
                self.update_worker_load(worker)
                self.calculate_worker_health(worker)
        return task

    def schedule_retry(self, task: ExecutionTask, reason: str | None = None) -> ExecutionTask:
        if task.retry_count >= task.max_retry:
            return self.complete_task(task, success=False, message=reason or "Max retry reached")
        task.retry_count += 1
        delay = self.retry_delay(task)
        task.next_retry_at = utc_now() + timedelta(seconds=delay)
        task.status = "RETRY_PENDING"
        task.queue_status = "RETRY_PENDING"
        task.error_message = reason
        queue = self.queue_for_task(task)
        if queue:
            queue.status = "RETRY_PENDING"
            queue.worker_node_id = None
            queue.lock_uuid = None
            queue.lock_expires_at = None
            queue.error_message = reason
        self.release_lock(task)
        execution_log(
            self.db,
            task,
            "RETRY_PENDING",
            new_status="RETRY_PENDING",
            message=reason,
            metadata={"retry_count": task.retry_count, "retry_delay_seconds": delay},
        )
        return task

    def recover_worker_tasks(self, worker: WorkerNode) -> list[ExecutionTask]:
        tasks = self.db.scalars(
            select(ExecutionTask).where(
                ExecutionTask.worker_node_id == worker.id,
                ExecutionTask.status.in_(["CLAIMED", "RUNNING"]),
            )
        ).all()
        for task in tasks:
            queue = self.queue_for_task(task)
            if queue:
                queue.status = "WORKER_LOST"
                queue.error_message = f"Worker lost: {worker.name}"
            old_status = task.status
            task.status = "WORKER_LOST"
            task.queue_status = "WORKER_LOST"
            execution_log(
                self.db,
                task,
                "WORKER_LOST",
                old_status=old_status,
                new_status="WORKER_LOST",
                message=f"Worker lost: {worker.name}",
            )
            self.schedule_retry(task, f"Worker lost: {worker.name}")
        self.update_worker_load(worker)
        return tasks

    def acquire_lock(self, task: ExecutionTask, worker: WorkerNode, ttl_seconds: int = 300) -> TaskLock | None:
        now = utc_now()
        existing = self.db.scalar(
            select(TaskLock).where(
                TaskLock.resource_type == "execution_task",
                TaskLock.resource_id == task.id,
                TaskLock.status == "ACTIVE",
                TaskLock.expires_at > now,
            )
        )
        if existing:
            return None
        lock = TaskLock(
            resource_type="execution_task",
            resource_id=task.id,
            owner_worker_id=worker.id,
            status="ACTIVE",
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self.db.add(lock)
        self.db.flush()
        return lock

    def release_lock(self, task: ExecutionTask) -> None:
        if not task.lock_uuid:
            return
        lock = self.db.scalar(select(TaskLock).where(TaskLock.uuid == task.lock_uuid))
        if lock:
            lock.status = "RELEASED"
        task.lock_uuid = None

    def best_worker(self, required_capability: str | None = None) -> WorkerNode | None:
        self.mark_stale_workers()
        workers = self.db.scalars(
            select(WorkerNode).where(WorkerNode.status == "ONLINE").order_by(
                WorkerNode.priority.asc(),
                WorkerNode.current_tasks.asc(),
                WorkerNode.health_score.desc(),
            )
        ).all()
        for worker in workers:
            self.update_worker_load(worker)
            if worker.current_tasks >= worker.max_concurrent_tasks:
                continue
            if required_capability and not self.worker_supports(worker, required_capability):
                continue
            return worker
        return None

    def worker_supports(self, worker: WorkerNode, capability: str | None) -> bool:
        if not capability:
            return True
        capabilities = self._normalize_capabilities(worker.capabilities or worker.capability or {})
        if capabilities.get("*") or capabilities.get("ALL"):
            return True
        return bool(capabilities.get(capability))

    def required_capability(self, task: ExecutionTask) -> str:
        payload = task.payload_json or {}
        if payload.get("capability_required"):
            return str(payload["capability_required"])
        action = (task.action_type or payload.get("action_type") or "OPEN_PAGE").upper()
        if action in {"PREPARE_REPLY", "REPLY"}:
            return "BROWSER"
        if action in {"ANALYZE", "GENERATE_REPLY"}:
            return "AI"
        return "BROWSER"

    def runtime_status(self) -> dict[str, Any]:
        self.mark_stale_workers()
        queue_length = self.count_queue("QUEUED") + self.count_queue("RETRY_PENDING")
        running = self.count_tasks("RUNNING")
        failed = self.count_tasks("FAILED")
        success = self.count_tasks("SUCCESS")
        total_finished = max(success + failed, 1)
        failure_rate = round((failed / total_finished) * 100, 2)
        return {
            "runtime": "AUTOMATION",
            "task_queue": queue_length,
            "online_workers": self.count_workers("ONLINE"),
            "offline_workers": self.count_workers("OFFLINE"),
            "running_tasks": running,
            "failed_tasks": failed,
            "success_tasks": success,
            "failure_rate": failure_rate,
            "throughput": success,
            "worker_lost": self.count_tasks("WORKER_LOST"),
            "retry_pending": self.count_tasks("RETRY_PENDING"),
        }

    def metrics(self) -> dict[str, Any]:
        status = self.runtime_status()
        for key, value in status.items():
            if isinstance(value, (int, float)):
                self.db.add(RuntimeMetric(metric=f"automation_{key}", value=float(value), dimension="SYSTEM"))
        if status["task_queue"] > 100:
            self.create_alert("QUEUE_TOO_LONG", "Automation queue length is above 100.", severity="WARNING")
        if status["failure_rate"] > 50:
            self.create_alert("FAILURE_RATE_HIGH", "Automation failure rate is above 50%.", severity="ERROR")
        return status

    def create_alert(self, alert_type: str, message: str, *, severity: str = "WARNING", metadata: dict[str, Any] | None = None) -> SystemAlert:
        existing = self.db.scalar(
            select(SystemAlert).where(
                SystemAlert.alert_type == alert_type,
                SystemAlert.status == "OPEN",
                SystemAlert.message == message,
            )
        )
        if existing:
            return existing
        alert = SystemAlert(alert_type=alert_type, severity=severity, status="OPEN", message=message, metadata_json=metadata or {})
        self.db.add(alert)
        self.db.flush()
        return alert

    def log(
        self,
        worker: WorkerNode | None,
        task: ExecutionTask | None,
        level: str,
        module: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> WorkerLog:
        item = WorkerLog(
            worker_node_id=worker.id if worker else None,
            worker_id=worker.name if worker else None,
            execution_task_id=task.id if task else None,
            log_type="automation",
            module=module,
            level=level.upper(),
            message=message,
            metadata_json=metadata or {},
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_worker_load(self, worker: WorkerNode) -> None:
        worker.current_tasks = self.db.scalar(
            select(func.count()).select_from(ExecutionTask).where(
                ExecutionTask.worker_node_id == worker.id,
                ExecutionTask.status.in_(["CLAIMED", "RUNNING", "WAITING_MANUAL"]),
            )
        ) or 0

    def calculate_worker_health(self, worker: WorkerNode) -> float:
        success = self.db.scalar(select(func.count()).select_from(ExecutionTask).where(ExecutionTask.worker_node_id == worker.id, ExecutionTask.status == "SUCCESS")) or 0
        failed = self.db.scalar(select(func.count()).select_from(ExecutionTask).where(ExecutionTask.worker_node_id == worker.id, ExecutionTask.status == "FAILED")) or 0
        total = max(success + failed, 1)
        worker.failure_rate = round((failed / total) * 100, 2)
        worker.task_success_rate = round((success / total) * 100, 2)
        resource_penalty = max(float(worker.cpu or 0) - 85, 0) * 0.2 + max(float(worker.memory or 0) - 85, 0) * 0.2
        heartbeat_penalty = 20 if worker.status != "ONLINE" else 0
        worker.health_score = max(0, min(100, 100 - worker.failure_rate - resource_penalty - heartbeat_penalty))
        return worker.health_score

    def retry_delay(self, task: ExecutionTask) -> int:
        base = int(task.retry_delay_seconds or 60)
        if (task.retry_strategy or "EXPONENTIAL").upper() == "EXPONENTIAL":
            return min(base * (2 ** max(task.retry_count - 1, 0)), 3600)
        return base

    def count_queue(self, status: str) -> int:
        return self.db.scalar(select(func.count()).select_from(ExecutionQueue).where(ExecutionQueue.status == status)) or 0

    def count_tasks(self, status: str) -> int:
        return self.db.scalar(select(func.count()).select_from(ExecutionTask).where(ExecutionTask.status == status)) or 0

    def count_workers(self, status: str) -> int:
        return self.db.scalar(select(func.count()).select_from(WorkerNode).where(WorkerNode.status == status)) or 0

    def queue_for_task(self, task: ExecutionTask) -> ExecutionQueue | None:
        return self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id))

    def find_worker(self, worker_id: Any) -> WorkerNode | None:
        if worker_id is None:
            return None
        if isinstance(worker_id, int) or str(worker_id).isdigit():
            worker = self.db.get(WorkerNode, int(worker_id))
            if worker:
                return worker
        return self.db.scalar(select(WorkerNode).where(WorkerNode.name == str(worker_id)))

    def _normalize_capabilities(self, capabilities: Any) -> dict[str, bool]:
        if isinstance(capabilities, list):
            return {str(item).upper(): True for item in capabilities}
        if isinstance(capabilities, dict):
            return {str(key).upper(): bool(value) for key, value in capabilities.items()}
        return {}

    def _float_or_none(self, value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
