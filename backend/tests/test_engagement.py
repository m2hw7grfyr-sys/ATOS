import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, AccountLimit, EngagementStrategy, EngagementTask, Platform, SchedulerTask
from app.services.engagement import create_engagement_task, execute_engagement_mock, queue_engagement_task


class EngagementWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
        self.db.flush()
        account = Account(platform_id=platform.id, username="engage_account", risk_status="LOW", status="ACTIVE")
        self.db.add(account)
        self.db.flush()
        self.db.add(AccountLimit(account_id=account.id))
        strategy = EngagementStrategy(
            name="Test Warmup",
            platform="reddit",
            strategy_type="REPLY_WARMUP",
            browse_count_min=2,
            browse_count_max=2,
            like_count_min=1,
            like_count_max=1,
            visit_profile_count_min=1,
            visit_profile_count_max=1,
            before_reply_enabled=True,
        )
        self.db.add(strategy)
        self.db.commit()
        self.account = account
        self.strategy = strategy

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_engagement_task_queue_and_mock_execution(self):
        task = create_engagement_task(
            self.db,
            {
                "strategy_id": self.strategy.id,
                "account_id": self.account.id,
                "platform": "reddit",
                "source_type": "POST_POOL",
                "source_value": "seed",
                "browse_target_count": 2,
                "like_target_count": 1,
                "visit_profile_target_count": 1,
                "priority": "MEDIUM",
            },
        )
        scheduler_task = queue_engagement_task(self.db, task)
        self.db.commit()
        self.assertEqual(task.status, "QUEUED")
        self.assertEqual(scheduler_task.task_type, "ENGAGEMENT")
        self.assertEqual(scheduler_task.payload["action_type"], "MIXED_ENGAGEMENT")

        execute_engagement_mock(self.db, task)
        self.db.commit()
        self.assertEqual(task.status, "SUCCESS")
        limit = self.db.scalar(select(AccountLimit).where(AccountLimit.account_id == self.account.id))
        self.assertEqual(limit.current_browse_count, 2)
        self.assertEqual(limit.current_like_count, 1)
        self.assertEqual(limit.current_visit_profile_count, 1)
        self.assertEqual(self.db.scalar(select(SchedulerTask).where(SchedulerTask.id == scheduler_task.id)).task_type, "ENGAGEMENT")


if __name__ == "__main__":
    unittest.main()
