import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import BrowserSession, BrowserTab, ReplayIndex, WorkerNode
from app.services.browser_runtime import BrowserRuntime


class BrowserRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.worker = WorkerNode(
            name="browser-test-worker",
            status="ONLINE",
            host="localhost",
            version="test",
            capability={"mode": "local"},
        )
        self.db.add(self.worker)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_open_close_and_recover_mock_tab(self):
        runtime = BrowserRuntime(self.db)
        tab = runtime.open_url(
            url="https://example.com/browser",
            browser_type="mock",
            worker_id=self.worker.id,
            execution_task_id=99,
        )
        self.db.commit()
        self.assertEqual(tab.status, "OPEN")
        session = self.db.get(BrowserSession, tab.session_id)
        self.assertEqual(session.status, "ATTACHED")
        replay = self.db.scalar(select(ReplayIndex).where(ReplayIndex.execution_task_id == 99))
        self.assertEqual(replay.manifest_json["tab_id"], tab.id)

        runtime.close_tab(tab.id)
        self.db.commit()
        self.assertEqual(tab.status, "CLOSED")

        session.status = "BROKEN"
        runtime.recover(session.id)
        self.db.commit()
        self.assertEqual(session.status, "RUNNING")
        self.assertEqual(len(self.db.scalars(select(BrowserTab)).all()), 1)


if __name__ == "__main__":
    unittest.main()
