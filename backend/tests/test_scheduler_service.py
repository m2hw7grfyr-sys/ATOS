import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AITask, Account, Platform, Post, Reply, SchedulerLog, TGEProfile
from app.services.scheduler import queue_approved_ai_task, run_once, save_scheduler_settings


def today_window():
    return {
        "timezone": "UTC",
        "windows": [
            {
                "day": datetime.now(timezone.utc).strftime("%a").upper()[:3],
                "start": "00:00",
                "end": "23:59",
            }
        ],
    }


class SchedulerServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(self.platform)
        self.db.flush()
        self.account = Account(
            platform_id=self.platform.id,
            username="scheduler_reddit",
            display_name="Scheduler Reddit",
            daily_limits={"reply": 5},
            working_time=today_window(),
            status="ACTIVE",
        )
        self.post = Post(
            platform_id=self.platform.id,
            title="Need a calmer workflow",
            content="What should I try first?",
            url="https://example.com/scheduler",
        )
        self.db.add_all([self.account, self.post])
        self.db.flush()
        self.db.add(
            TGEProfile(
                account_id=self.account.id,
                bound_account_id=self.account.id,
                platform_id=self.platform.id,
                environment_id="scheduler-env",
                tge_environment_id="scheduler-env",
                name="Scheduler Env",
                profile_name="Scheduler Env",
                status="ACTIVE",
            )
        )
        self.ai_task = AITask(
            post_id=self.post.id,
            provider="mock",
            model="mock-v0.3",
            strategy="PURE_HELP",
            status="APPROVED",
        )
        self.db.add(self.ai_task)
        self.db.flush()
        self.reply = Reply(
            post_id=self.post.id,
            ai_task_id=self.ai_task.id,
            content="Try one small weekly review.",
            source="MOCK",
            status="APPROVED",
        )
        self.db.add(self.reply)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_queue_approved_then_dispatch_placeholder(self):
        task = queue_approved_ai_task(self.db, ai_task_id=self.ai_task.id)
        self.db.commit()
        self.assertEqual(task.status, "QUEUED")

        save_scheduler_settings(
            self.db,
            {
                "scheduler_enabled": True,
                "enable_random_delay": False,
                "enable_platform_round_robin": True,
            },
        )
        result = run_once(self.db)
        self.assertEqual(result["status"], "DISPATCHED")
        self.assertEqual(task.account_id, self.account.id)
        self.assertEqual(task.status, "DISPATCHED")
        self.assertIn("execution_placeholder", task.payload)

        logs = self.db.scalars(select(SchedulerLog)).all()
        self.assertGreaterEqual(len(logs), 3)

    def test_random_delay(self):
        task = queue_approved_ai_task(self.db, ai_task_id=self.ai_task.id)
        self.db.commit()
        save_scheduler_settings(
            self.db,
            {
                "scheduler_enabled": True,
                "enable_random_delay": True,
                "min_delay_seconds": 5,
                "max_delay_seconds": 5,
            },
        )
        result = run_once(self.db)
        self.assertEqual(result["status"], "DELAYED")
        self.assertEqual(task.status, "DELAYED")
        self.assertEqual(task.delay_seconds, 5)
        self.assertIsNotNone(task.earliest_execute_at)


if __name__ == "__main__":
    unittest.main()
