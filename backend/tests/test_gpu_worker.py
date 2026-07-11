import os
import unittest
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base
from app.models import GPUGenerationTask, GPUWorkerStatus
from app.services.gpu_worker import GPUWorkerService, require_gpu_worker_bearer, utc_now


class GPUWorkerApiTest(unittest.TestCase):
    def setUp(self):
        os.environ["GPU_WORKER_API_KEY"] = "test-gpu-worker-token"
        os.environ["GPU_HEARTBEAT_TIMEOUT_SECONDS"] = "1"
        os.environ["GPU_TASK_LEASE_SECONDS"] = "600"
        get_settings.cache_clear()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        get_settings.cache_clear()

    def _db(self):
        return self.Session()

    def _heartbeat_payload(self, worker_id="worker-a"):
        return {
            "worker_id": worker_id,
            "worker_name": worker_id,
            "worker_type": "gpu",
            "status": "idle",
            "version": "test",
            "ollama_reachable": True,
            "ollama_version": "0.31.2",
            "model_name": "llama3.1:8b",
        }

    def test_missing_and_wrong_token_are_unauthorized(self):
        with self.assertRaises(HTTPException) as missing:
            require_gpu_worker_bearer(None)
        with self.assertRaises(HTTPException) as wrong:
            require_gpu_worker_bearer("Bearer wrong")

        self.assertEqual(missing.exception.status_code, 401)
        self.assertEqual(wrong.exception.status_code, 401)

    def test_heartbeat_creates_and_updates_worker(self):
        with self._db() as db:
            service = GPUWorkerService(db)
            service.heartbeat(self._heartbeat_payload())
            db.commit()
            worker = db.scalar(select(GPUWorkerStatus).where(GPUWorkerStatus.worker_id == "worker-a"))
            self.assertIsNotNone(worker)
            self.assertEqual(worker.status, "idle")
            self.assertEqual(worker.ollama_version, "0.31.2")

    def test_stale_worker_is_marked_offline(self):
        with self._db() as db:
            service = GPUWorkerService(db)
            worker = service.heartbeat(self._heartbeat_payload())
            worker.last_heartbeat_at = utc_now() - timedelta(seconds=30)
            db.commit()

            service.mark_offline_workers()
            db.commit()

            self.assertEqual(worker.status, "offline")

    def test_no_task_returns_null(self):
        with self._db() as db:
            task = GPUWorkerService(db).lease_next(
                worker_id="worker-a",
                supported_models=["llama3.1:8b"],
            )
            self.assertIsNone(task)

    def test_atomic_lease_and_no_duplicate_claim(self):
        with self._db() as db:
            task = GPUWorkerService(db).create_task(
                prompt="hello",
                system_prompt=None,
                model="llama3.1:8b",
                options={},
            )
            task_id = task.id
            db.commit()

        with self._db() as db:
            service = GPUWorkerService(db)
            first = service.lease_next(worker_id="worker-a", supported_models=["llama3.1:8b"])
            second = service.lease_next(worker_id="worker-b", supported_models=["llama3.1:8b"])
            self.assertEqual(first.id, task_id)
            self.assertIsNone(second)

    def test_complete_writes_result_and_is_idempotent(self):
        with self._db() as db:
            service = GPUWorkerService(db)
            task = service.create_task(prompt="hello", system_prompt=None, model="llama3.1:8b", options={})
            leased = service.lease_next(worker_id="worker-a", supported_models=["llama3.1:8b"])
            service.mark_started(leased.id, "worker-a")
            db.commit()
            task_id = task.id

        with self._db() as db:
            service = GPUWorkerService(db)
            service.complete(
                task_id,
                worker_id="worker-a",
                result_text="first",
                metrics={"duration_ms": 1},
            )
            service.complete(
                task_id,
                worker_id="worker-a",
                result_text="second",
                metrics={"duration_ms": 2},
            )
            db.commit()
            task = db.get(GPUGenerationTask, task_id)
            self.assertEqual(task.status, "completed")
            self.assertEqual(task.result_text, "first")

    def test_failed_records_error(self):
        with self._db() as db:
            service = GPUWorkerService(db)
            task = service.create_task(prompt="hello", system_prompt=None, model="llama3.1:8b", options={})
            leased = service.lease_next(worker_id="worker-a", supported_models=["llama3.1:8b"])
            db.commit()
            task_id = leased.id

        with self._db() as db:
            service = GPUWorkerService(db)
            service.fail(
                task_id,
                worker_id="worker-a",
                error_type="OllamaError",
                error_message="ollama unavailable",
                retryable=False,
            )
            db.commit()
            task = db.get(GPUGenerationTask, task_id)
            self.assertEqual(task.status, "failed")
            self.assertEqual(task.error_type, "OllamaError")
            self.assertIn("ollama", task.error_message)

    def test_expired_lease_can_be_reclaimed(self):
        with self._db() as db:
            service = GPUWorkerService(db)
            task = service.create_task(prompt="hello", system_prompt=None, model="llama3.1:8b", options={})
            leased = service.lease_next(worker_id="worker-a", supported_models=["llama3.1:8b"])
            leased.lease_expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
            task_id = task.id

        with self._db() as db:
            task = GPUWorkerService(db).lease_next(
                worker_id="worker-b",
                supported_models=["llama3.1:8b"],
            )
            self.assertEqual(task.id, task_id)
            self.assertEqual(task.worker_id, "worker-b")


if __name__ == "__main__":
    unittest.main()
