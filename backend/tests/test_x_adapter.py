import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.x import XAdapter, normalize_x_post_url
from app.database import Base
from app.models import Account, ExecutionLog, Platform, Post, Reply, ReplyTask, TGEProfile
from app.services.platform_runtime import PlatformRuntime
from app.services.reply_pipeline import ReplyPipelineService


class XAdapterTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.platform = Platform(name="X", slug="x", adapter_key="x")
        self.db.add(self.platform)
        self.db.flush()
        self.account = Account(platform_id=self.platform.id, username="atos_x_test", status="ACTIVE", risk_status="LOW")
        self.db.add(self.account)
        self.db.flush()
        self.profile = TGEProfile(
            account_id=self.account.id,
            bound_account_id=self.account.id,
            platform_id=self.platform.id,
            tge_environment_id="x-test-env",
            environment_id="x-test-env",
            connection_status="SUCCESS",
            runtime_status="RUNNING",
            status="ACTIVE",
        )
        self.post = Post(
            platform_id=self.platform.id,
            source_post_id="1234567890",
            title="X test post",
            content="How should I structure this workflow?",
            url="https://x.com/builder/status/1234567890",
            raw_json={"author_handle": "builder", "external_post_id": "1234567890"},
            status="WAITING_REVIEW",
        )
        self.db.add_all([self.profile, self.post])
        self.db.flush()
        self.reply = Reply(post_id=self.post.id, content="Start with one visible queue and one daily review.", status="APPROVED")
        self.db.add(self.reply)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_normalize_x_urls(self):
        normalized = normalize_x_post_url("https://twitter.com/builder/status/1234567890?s=20")
        self.assertTrue(normalized["valid"])
        self.assertEqual(normalized["platform"], "x")
        self.assertEqual(normalized["external_post_id"], "1234567890")
        self.assertEqual(normalized["canonical_url"], "https://x.com/builder/status/1234567890")

    def test_x_capability_and_mock_fill(self):
        runtime = PlatformRuntime(self.db, mock_mode=True)
        capability = runtime.check_capability("x", "PREPARE_REPLY")
        self.assertTrue(capability["supported"])
        adapter = XAdapter(self.db, mock_mode=True)
        self.assertTrue(adapter.open_post(None, self.post.url)["opened"])
        self.assertTrue(adapter.find_reply_box(None)["found"])
        self.assertTrue(adapter.fill_reply(None, self.reply.content)["filled"])

    def test_x_test_mode_failures(self):
        adapter = XAdapter(self.db, mock_mode=True)
        self.assertTrue(adapter.detect_login_required({"test_mode": "login_required"})["detected"])
        self.assertTrue(adapter.detect_rate_limit({"test_mode": "rate_limited"})["detected"])
        self.assertFalse(adapter.find_reply_box({"test_mode": "reply_box_not_found"})["found"])
        self.assertEqual(adapter.open_post({"test_mode": "browser_disconnected"}, self.post.url)["code"], "BROWSER_DISCONNECTED")

    def test_x_reply_pipeline_reaches_waiting_manual_and_confirmed(self):
        service = ReplyPipelineService(self.db, trace_id="x-test")
        reply_task = service.approve_reply(reply_id=self.reply.id, account_id=self.account.id)
        self.assertEqual(reply_task.platform, "x")
        scheduler = service.schedule_reply_task(reply_task.id, account_id=self.account.id)
        execution = service.create_execution_task(reply_task.id)
        prepared = service.prepare_reply(reply_task.id)
        self.assertEqual(prepared.status, "WAITING_MANUAL")
        self.assertEqual(execution.platform, "x")

        actions = [
            row.action
            for row in self.db.scalars(
                select(ExecutionLog).where(ExecutionLog.execution_task_id == execution.id)
            ).all()
        ]
        self.assertIn("OPEN_POST_STARTED", actions)
        self.assertIn("REPLY_BOX_FOUND", actions)
        self.assertIn("REPLY_FILLED", actions)

        confirmed = service.confirm(reply_task.id)
        self.assertEqual(confirmed.status, "CONFIRMED")
        self.assertEqual(scheduler.status, "EXECUTED")
        self.assertEqual(self.db.get(ReplyTask, reply_task.id).status, "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
