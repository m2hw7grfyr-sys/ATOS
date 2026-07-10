import os
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import WorkerLog, WorkerNode
from app.config import get_settings
from app.services.remote_worker import RemoteWorkerService


class RemoteWorkerTest(unittest.TestCase):
    def setUp(self):
        os.environ["WORKER_API_TOKEN"] = "test-token"
        get_settings.cache_clear()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_register_heartbeat_and_restart(self):
        service = RemoteWorkerService(self.db)
        worker = service.register(
            {
                "name": "windows-ai-01",
                "hostname": "WIN-AI-01",
                "os": "Windows",
                "ip": "10.0.0.5",
                "version": "sprint-06",
                "runtime_status": "READY",
                "capabilities": {"AI": True, "Browser": True, "TGE": True},
            }
        )
        self.assertEqual(worker.status, "ONLINE")
        self.assertTrue(worker.capabilities["AI"])

        worker = service.heartbeat(
            {
                "worker_id": "windows-ai-01",
                "cpu": 12.5,
                "memory": 40.2,
                "gpu": 5.0,
                "runtime_status": "READY",
                "capabilities": {"AI": True, "Browser": True, "TGE": True, "Playwright": True},
            }
        )
        self.assertEqual(worker.cpu, 12.5)
        self.assertEqual(worker.runtime_status, "READY")

        restarted = service.restart(worker.id)
        self.assertEqual(restarted.runtime_status, "RESTART_REQUESTED")

        logs = self.db.scalars(select(WorkerLog).where(WorkerLog.worker_node_id == worker.id)).all()
        self.assertGreaterEqual(len(logs), 3)
        self.assertEqual(self.db.scalar(select(WorkerNode)).name, "windows-ai-01")


if __name__ == "__main__":
    unittest.main()
