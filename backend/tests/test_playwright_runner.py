import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, ExecutionTask, Platform, ReplayFile, TGEProfile
from app.services.execution import run_precheck
from app.services.playwright_runner import run_open_page


class PlaywrightRunnerTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
        self.db.flush()
        account = Account(platform_id=platform.id, username="pw_account", risk_status="LOW", status="ACTIVE")
        self.db.add(account)
        self.db.flush()
        profile = TGEProfile(
            account_id=account.id,
            bound_account_id=account.id,
            platform_id=platform.id,
            tge_environment_id="pw-env",
            websocket_url="mock://pw-env",
            connection_status="SUCCESS",
            runtime_status="RUNNING",
            status="ACTIVE",
        )
        self.db.add(profile)
        self.db.flush()
        self.task = ExecutionTask(
            account_id=account.id,
            tge_profile_id=profile.id,
            platform="reddit",
            action_type="OPEN_PAGE",
            payload_json={"url": "https://example.com/post"},
            status="RECEIVED",
        )
        self.db.add(self.task)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_mock_open_page_generates_replay(self):
        run_precheck(self.db, self.task)
        run_open_page(self.db, self.task)
        self.db.commit()
        self.assertEqual(self.task.status, "SUCCESS")
        replay = self.db.scalar(select(ReplayFile).where(ReplayFile.execution_task_id == self.task.id))
        self.assertTrue(replay.screenshot_path)
        self.assertTrue(replay.html_path)


if __name__ == "__main__":
    unittest.main()
