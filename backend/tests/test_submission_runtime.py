import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, AutoAssistedPlatformConfig, BrowserSession, ExecutionTask, Platform, PlatformRegistry, Post, Reply, ReplyTask, ReplyTemplate, SchedulerTask, SubmissionTask, WorkerNode
from app.services.reply_template_strategy import ensure_reply_template_seed
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
        ensure_reply_template_seed(self.db)
        self.safe_template = self.db.scalar(select(ReplyTemplate).where(ReplyTemplate.funnel_intent == "NO_CTA"))
        self.registry = PlatformRegistry(
            platform_name="reddit",
            adapter_name="RedditAdapter",
            capabilities={"AUTO_SUBMIT": True, "REPLY": True},
            status="HEALTHY",
        )
        self.db.add(self.registry)
        self.db.flush()
        self.account = Account(
            platform_id=self.platform.id,
            username="submission_account",
            status="ACTIVE",
            risk_status="LOW",
            allow_auto_assisted=False,
        )
        self.db.add(self.account)
        self.db.flush()
        self.worker = WorkerNode(name="local-test-worker", status="ONLINE", host="localhost", version="test", capability={"BROWSER": True})
        self.db.add(self.worker)
        self.db.flush()
        self.session = BrowserSession(
            browser_type="mock",
            worker_id=self.worker.id,
            account_id=self.account.id,
            status="RUNNING",
            metadata_json={"test": True},
        )
        self.db.add(self.session)
        self.db.flush()
        self.platform_config = AutoAssistedPlatformConfig(
            platform="reddit",
            auto_assisted_enabled=False,
            max_daily_auto_submit=3,
            allowed_accounts=[],
            allowed_time_window={},
        )
        self.db.add(self.platform_config)
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
            reply_template_id=self.safe_template.id if self.safe_template else None,
            funnel_intent="NO_CTA",
            cta_strength="NONE",
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
            worker_node_id=self.worker.id,
            action_type="PREPARE_REPLY",
            payload_json={
                "platform": "reddit",
                "reply_content": self.reply.content,
                "browser_tab_id": None,
                "browser_session_id": self.session.id,
            },
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
        self.assertEqual(task.operator_id, "operator")
        self.assertIsNotNone(task.confirmed_at)
        self.assertIn(task.verification_level, {"MANUAL_CONFIRMED", "URL_VERIFIED", "EXTERNAL_ID_VERIFIED"})
        self.assertEqual(self.reply_task.status, "CONFIRMED")
        self.assertEqual(self.execution.status, "SUCCESS")
        self.assertEqual(self.scheduler.status, "EXECUTED")
        self.assertEqual(runtime.contract(task)["platform"], "reddit")

    def test_auto_assisted_disabled_by_policy(self):
        save_submission_settings(self.db, {"default_execution_mode": "AUTO_ASSISTED", "auto_assisted_enabled": False})
        self.reply_task.execution_mode = "AUTO_ASSISTED"
        self.execution.payload_json = {**self.execution.payload_json, "execution_mode": "AUTO_ASSISTED"}
        task = SubmissionRuntime(self.db, trace_id="test").prepare_submission(
            reply_task=self.reply_task,
            execution=self.execution,
        )
        self.assertEqual(task.status, "MANUAL_REQUIRED")

    def test_mark_failed_and_retry_guard(self):
        runtime = SubmissionRuntime(self.db, trace_id="test")
        task = runtime.prepare_submission(reply_task=self.reply_task, execution=self.execution)
        failed = runtime.mark_failed(task.id, "LOGIN_REQUIRED")
        self.assertEqual(failed.status, "MANUAL_REQUIRED")
        self.assertEqual(failed.error_code, "LOGIN_REQUIRED")
        retried = runtime.retry(failed.id)
        self.assertEqual(retried.status, "MANUAL_REQUIRED")
        self.assertIn("operator", retried.retry_blocked_reason.lower())

    def test_retry_allowed_for_browser_disconnect_once(self):
        runtime = SubmissionRuntime(self.db, trace_id="test")
        task = runtime.prepare_submission(reply_task=self.reply_task, execution=self.execution)
        failed = runtime.mark_failed(task.id, "BROWSER_DISCONNECTED")
        self.assertEqual(failed.status, "RETRY_PENDING")
        retried = runtime.retry(failed.id)
        self.assertEqual(retried.status, "PREPARED")
        self.assertEqual(retried.retry_count, 1)

    def test_auto_assisted_test_mode_completes_with_all_guards_enabled(self):
        save_submission_settings(
            self.db,
            {
                "default_execution_mode": "AUTO_ASSISTED",
                "auto_assisted_enabled": True,
                "auto_assisted_test_mode": True,
            },
        )
        self.platform_config.auto_assisted_enabled = True
        self.account.allow_auto_assisted = True
        self.reply_task.status = "APPROVED"
        self.reply_task.execution_mode = "AUTO_ASSISTED"
        self.execution.payload_json = {**self.execution.payload_json, "execution_mode": "AUTO_ASSISTED"}
        runtime = SubmissionRuntime(self.db, trace_id="test")
        task = runtime.prepare_submission(reply_task=self.reply_task, execution=self.execution)
        self.assertEqual(task.status, "PREPARED")
        completed = runtime.submit_reply(task.id)
        self.assertEqual(completed.status, "COMPLETED")
        self.assertEqual(completed.verification_level, "EXTERNAL_ID_VERIFIED")

    def test_emergency_stop_moves_auto_assisted_tasks_to_waiting_manual(self):
        save_submission_settings(self.db, {"default_execution_mode": "AUTO_ASSISTED", "auto_assisted_enabled": True})
        self.reply_task.execution_mode = "AUTO_ASSISTED"
        runtime = SubmissionRuntime(self.db, trace_id="test")
        task = runtime.get_or_create(reply_task=self.reply_task, execution=self.execution)
        task.status = "SUBMITTING"
        result = runtime.emergency_stop()
        self.assertEqual(result["affected_tasks"], 1)
        self.assertEqual(task.status, "WAITING_MANUAL")
        self.assertFalse(get_submission_settings(self.db)["auto_assisted_enabled"])


if __name__ == "__main__":
    unittest.main()
