import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, ExecutionTask, Platform, Post, Reply, ReplyTask, SchedulerTask, SubmissionTask
from app.services.submission_runtime import SubmissionRuntime, get_submission_settings, save_submission_settings


class SubmissionRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(self.platform)
        self.db.flush()
        self.account = Account(platform_id=self.platform.id, username="submission_account", status="ACTIVE", risk_status="LOW")
        self.db.add(self.account)
        self.db.flush()
        self.post = Post(platform_id=self.platform.id, title="Need a focus workflow", url="https://example.com/post")
        self.db.add(self.post)
        self.db.flush()
        self.reply = Reply(post_id=self.post.id, content="Try one repeatable checklist before changing tools.", status="APPROVED")
        self.db.add(self.reply)
        self.db.flush()
        self.reply_task = ReplyTask(
            post_id=self.post.id,
            reply_id=self.reply.id,
            platform="reddit",
            account_id=self.account.id,
            reply_content=self.reply.content,
            execution_mode="SEMI_AUTO",
            status="WAITING_MANUAL",
        )
        self.db.add(self.reply_task)
        self.db.flush()
        self.scheduler = SchedulerTask(
            task_type="REPLY_TASK",
            platform_id=self.platform.id,
            account_id=self.account.id,
            post_id=self.post.id,
            reply_id=self.reply.id,
            reply_task_id=self.reply_task.id,
            payload={"platform": "reddit", "reply_content": self.reply.content},
            status="DISPATCHED",
        )
        self.db.add(self.scheduler)
        self.db.flush()
        self.execution = ExecutionTask(
            scheduler_task_id=self.scheduler.id,
            reply_task_id=self.reply_task.id,
            account_id=self.account.id,
            platform="reddit",
            action_type="PREPARE_REPLY",
            payload_json={"platform": "reddit", "reply_content": self.reply.content, "browser_tab_id": None},
            status="WAITING_MANUAL",
            queue_status="WAITING_MANUAL",
        )
        self.db.add(self.execution)
        self.db.flush()
        self.reply_task.scheduler_task_id = self.scheduler.id
        self.reply_task.execution_task_id = self.execution.id
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_default_policy_is_semi_auto_and_blocks_auto_submit(self):
        settings = get_submission_settings(self.db)
        self.assertEqual(settings["default_execution_mode"], "SEMI_AUTO")
        self.assertFalse(settings["auto_assisted_enabled"])

        runtime = SubmissionRuntime(self.db, trace_id="test")
        submission = runtime.prepare_submission(reply_task=self.reply_task, execution=self.execution)
        self.assertEqual(submission.status, "WAITING_MANUAL")

        evaluated = runtime.submit_reply(submission.id)
        self.assertEqual(evaluated.status, "WAITING_MANUAL")
        self.assertIn("human", evaluated.failure_reason.lower())

    def test_manual_result_records_verified_submission(self):
        runtime = SubmissionRuntime(self.db, trace_id="test")
        task = runtime.record_manual_result(
            reply_task=self.reply_task,
            execution=self.execution,
            scheduler=self.scheduler,
        )
        self.assertEqual(task.status, "VERIFIED")
        self.assertTrue(task.manual_confirmed)
        self.assertEqual(self.reply_task.status, "CONFIRMED")
        self.assertEqual(self.execution.status, "SUCCESS")
        self.assertEqual(self.scheduler.status, "EXECUTED")

    def test_auto_assisted_disabled_by_policy(self):
        save_submission_settings(self.db, {"default_execution_mode": "AUTO_ASSISTED", "auto_assisted_enabled": False})
        self.reply_task.execution_mode = "AUTO_ASSISTED"
        self.execution.payload_json = {**self.execution.payload_json, "execution_mode": "AUTO_ASSISTED"}
        task = SubmissionRuntime(self.db, trace_id="test").prepare_submission(
            reply_task=self.reply_task,
            execution=self.execution,
        )
        self.assertEqual(task.status, "WAITING_POLICY")


if __name__ == "__main__":
    unittest.main()
