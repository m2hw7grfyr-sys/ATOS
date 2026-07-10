import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, AccountLimit, AITask, BrowserTab, Platform, Post, Reply, ReplyTask, SchedulerTask, TGEProfile
from app.services.reply_pipeline import ReplyPipelineService


class ReplyPipelineTest(unittest.TestCase):
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
            username="reply_pipeline_account",
            risk_status="LOW",
            status="ACTIVE",
        )
        self.db.add(self.account)
        self.db.flush()
        self.db.add(AccountLimit(account_id=self.account.id, reply_daily_limit=5))
        self.profile = TGEProfile(
            account_id=self.account.id,
            bound_account_id=self.account.id,
            platform_id=self.platform.id,
            tge_environment_id="reply-pipeline-env",
            environment_id="reply-pipeline-env",
            connection_status="SUCCESS",
            runtime_status="RUNNING",
            status="ACTIVE",
        )
        self.post = Post(
            platform_id=self.platform.id,
            title="How do I keep momentum?",
            content="I lose track after a few days.",
            url="https://example.com/reply-pipeline",
            status="WAITING_REVIEW",
        )
        self.db.add_all([self.profile, self.post])
        self.db.flush()
        self.ai_task = AITask(
            post_id=self.post.id,
            provider="mock",
            model="mock-v0.3",
            strategy="PURE_HELP",
            status="GENERATED",
        )
        self.db.add(self.ai_task)
        self.db.flush()
        self.reply = Reply(
            post_id=self.post.id,
            ai_task_id=self.ai_task.id,
            content="Start with one repeatable step and keep it visible.",
            source="MOCK",
            status="GENERATED",
        )
        self.db.add(self.reply)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_semi_auto_reply_pipeline_reaches_confirmed(self):
        service = ReplyPipelineService(self.db, trace_id="test")

        reply_task = service.approve_reply(reply_id=self.reply.id, account_id=self.account.id)
        self.assertEqual(reply_task.status, "APPROVED")
        self.assertEqual(reply_task.execution_mode, "SEMI_AUTO")

        scheduler_task = service.schedule_reply_task(reply_task.id, account_id=self.account.id)
        self.assertEqual(scheduler_task.task_type, "REPLY_TASK")
        self.assertEqual(scheduler_task.reply_task_id, reply_task.id)

        execution_task = service.create_execution_task(reply_task.id)
        self.assertEqual(execution_task.reply_task_id, reply_task.id)
        self.assertEqual(execution_task.payload_json["reply_content"], self.reply.content)

        prepared = service.prepare_reply(reply_task.id)
        self.assertEqual(prepared.status, "WAITING_MANUAL")
        self.assertEqual(self.db.get(ReplyTask, reply_task.id).status, "WAITING_MANUAL")

        confirmed = service.confirm(reply_task.id)
        self.assertEqual(confirmed.status, "CONFIRMED")
        self.assertEqual(self.db.get(SchedulerTask, scheduler_task.id).status, "EXECUTED")
        self.assertEqual(self.db.get(BrowserTab, execution_task.payload_json["browser_tab_id"]).status, "CLOSED")

        limit = self.db.scalar(select(AccountLimit).where(AccountLimit.account_id == self.account.id))
        self.assertEqual(limit.current_reply_count, 1)


if __name__ == "__main__":
    unittest.main()
