import unittest
from datetime import timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ExecutionQueue, ExecutionTask, TaskLock, WorkerNode
from app.services.automation_runtime import AutomationRuntime, utc_now


class AutomationRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def _task(self, status="QUEUED", capability="BROWSER", priority="NORMAL"):
        task = ExecutionTask(
            platform="reddit",
            action_type="OPEN_PAGE",
            payload_json={"capability_required": capability},
            status=status,
            queue_status=status,
            precheck_status="PENDING",
            environment_status="UNKNOWN",
        )
        self.db.add(task)
        self.db.flush()
        self.db.add(
            ExecutionQueue(
                execution_task_id=task.id,
                status=status,
                priority=priority,
                required_capability=capability,
            )
        )
        self.db.flush()
        return task

    def test_worker_registration_and_capability_claim(self):
        runtime = AutomationRuntime(self.db)
        worker = runtime.register_worker(
            {
                "name": "windows-browser-01",
                "capabilities": {"BROWSER": True},
                "max_concurrent_tasks": 2,
                "priority": 10,
            }
        )
        task = self._task(capability="BROWSER", priority="HIGH")

        claimed = runtime.claim_next(worker.id)

        self.assertEqual(claimed.id, task.id)
        self.assertEqual(claimed.status, "CLAIMED")
        self.assertEqual(claimed.claimed_by_worker, "windows-browser-01")
        self.assertIsNotNone(claimed.lock_uuid)

    def test_concurrency_limit_prevents_extra_claim(self):
        runtime = AutomationRuntime(self.db)
        worker = runtime.register_worker(
            {
                "name": "small-worker",
                "capabilities": {"BROWSER": True},
                "max_concurrent_tasks": 1,
            }
        )
        self._task(status="RUNNING", capability="BROWSER")
        running = self.db.scalar(select(ExecutionTask).where(ExecutionTask.status == "RUNNING"))
        running.worker_node_id = worker.id
        self._task(capability="BROWSER")
        runtime.update_worker_load(worker)

        claimed = runtime.claim_next(worker.id)

        self.assertIsNone(claimed)

    def test_existing_lock_blocks_duplicate_claim(self):
        runtime = AutomationRuntime(self.db)
        worker = runtime.register_worker({"name": "worker-a", "capabilities": {"BROWSER": True}})
        task = self._task(capability="BROWSER")
        self.db.add(
            TaskLock(
                resource_type="execution_task",
                resource_id=task.id,
                owner_worker_id=worker.id,
                status="ACTIVE",
                expires_at=utc_now() + timedelta(minutes=5),
            )
        )
        self.db.flush()

        claimed = runtime.claim_next(worker.id)

        self.assertIsNone(claimed)

    def test_worker_lost_moves_running_task_to_retry_pending(self):
        runtime = AutomationRuntime(self.db)
        worker = runtime.register_worker({"name": "worker-lost", "capabilities": {"BROWSER": True}})
        task = self._task(status="RUNNING", capability="BROWSER")
        task.worker_node_id = worker.id
        task.claimed_by_worker = worker.name
        queue = self.db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == task.id))
        queue.worker_node_id = worker.id
        queue.status = "RUNNING"

        recovered = runtime.recover_worker_tasks(worker)

        self.assertEqual(len(recovered), 1)
        self.assertEqual(task.status, "RETRY_PENDING")
        self.assertEqual(queue.status, "RETRY_PENDING")
        self.assertEqual(task.retry_count, 1)


if __name__ == "__main__":
    unittest.main()
