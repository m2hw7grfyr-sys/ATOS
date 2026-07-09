import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, AccountLimit, ExecutionTask, Platform, PlatformSelector, Post, Reply, SchedulerTask, TGEProfile
from app.services.execution import create_execution_task_from_scheduler, run_precheck
from app.services.playwright_runner import mark_submitted, prepare_reply


class SemiAutoReplyFlowTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
        self.db.flush()
        account = Account(platform_id=platform.id, username="reply_account", risk_status="LOW", status="ACTIVE")
        self.db.add(account)
        self.db.flush()
        self.db.add(AccountLimit(account_id=account.id, reply_daily_limit=5, current_reply_count=0))
        profile = TGEProfile(
            account_id=account.id,
            bound_account_id=account.id,
            platform_id=platform.id,
            tge_environment_id="reply-env",
            websocket_url="mock://reply-env",
            connection_status="SUCCESS",
            runtime_status="RUNNING",
            status="ACTIVE",
        )
        post = Post(
            platform_id=platform.id,
            source_post_id="reply-post",
            url_hash="reply-post",
            title="Need workflow help",
            content="How should I start?",
            url="https://example.com/reddit/reply-post",
            raw_json={"seed": True},
        )
        self.db.add_all([profile, post])
        self.db.flush()
        reply = Reply(post_id=post.id, content="Start with one small repeatable step.", status="APPROVED")
        self.db.add(reply)
        self.db.flush()
        scheduler_task = SchedulerTask(
            task_type="REPLY",
            platform_id=platform.id,
            account_id=account.id,
            post_id=post.id,
            reply_id=reply.id,
            payload={
                "action_type": "PREPARE_REPLY",
                "url": post.url,
                "post_url": post.url,
                "reply_content": reply.content,
            },
            status="DISPATCHED",
        )
        self.db.add(scheduler_task)
        self.db.add(
            PlatformSelector(
                platform="reddit",
                selector_key="reply_box",
                selector_value='div[contenteditable="true"]',
                selector_type="css",
                enabled=True,
            )
        )
        self.db.commit()
        self.scheduler_task = scheduler_task

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_prepare_reply_waits_for_manual_then_marks_success(self):
        task = create_execution_task_from_scheduler(self.db, self.scheduler_task)
        run_precheck(self.db, task)
        prepare_reply(self.db, task)
        self.db.commit()
        self.assertEqual(task.status, "WAITING_MANUAL")
        self.assertEqual(task.payload_json["fill_status"], "REPLY_FILLED")

        mark_submitted(self.db, task)
        self.db.commit()
        self.assertEqual(task.status, "SUCCESS")
        self.assertTrue(task.payload_json["manual_confirmed"])
        self.assertEqual(self.scheduler_task.status, "EXECUTED")
        limit = self.db.scalar(select(AccountLimit).where(AccountLimit.account_id == task.account_id))
        self.assertEqual(limit.current_reply_count, 1)


if __name__ == "__main__":
    unittest.main()
