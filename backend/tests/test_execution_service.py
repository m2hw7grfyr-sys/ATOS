import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, ExecutionQueue, ExecutionTask, Platform, SchedulerTask, TGEProfile
from app.services.execution import ExecutionRuntime, create_execution_task_from_scheduler, run_precheck


class ExecutionServiceTest(unittest.TestCase):
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
            username="execution_account",
            risk_status="LOW",
            status="ACTIVE",
        )
        self.db.add(self.account)
        self.db.flush()
        self.profile = TGEProfile(
            account_id=self.account.id,
            bound_account_id=self.account.id,
            platform_id=self.platform.id,
            tge_environment_id="env-execution",
            environment_id="env-execution",
            profile_name="Execution Env",
            connection_status="SUCCESS",
            runtime_status="UNKNOWN",
            status="ACTIVE",
        )
        self.task = SchedulerTask(
            task_type="REPLY",
            platform_id=self.platform.id,
            account_id=self.account.id,
            payload={"strategy": "PURE_HELP", "action_type": "OPEN_PAGE"},
            status="DISPATCHED",
        )
        self.db.add_all([self.profile, self.task])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_create_execution_task_and_precheck_success(self):
        execution = create_execution_task_from_scheduler(self.db, self.task)
        self.db.commit()
        self.assertEqual(execution.status, "QUEUED")
        run_precheck(self.db, execution)
        self.db.commit()
        self.assertEqual(execution.status, "ENVIRONMENT_READY")
        self.assertEqual(execution.precheck_status, "SUCCESS")
        self.assertEqual(self.db.scalar(select(ExecutionTask)).id, execution.id)

    def test_runtime_claim_retry_and_cancel(self):
        runtime = ExecutionRuntime(self.db, worker_name="test-worker")
        execution = runtime.push_scheduler_task(self.task)
        self.db.commit()
        self.assertEqual(execution.status, "QUEUED")
        self.assertIsNotNone(self.db.scalar(select(ExecutionQueue)))

        claimed = runtime.claim_next()
        self.db.commit()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.status, "CLAIMED")

        runtime.run_claimed(claimed)
        self.db.commit()
        self.assertEqual(claimed.status, "RUNNING")

        runtime.retry(claimed.id)
        self.db.commit()
        self.assertEqual(claimed.status, "QUEUED")
        self.assertEqual(claimed.retry_count, 1)

        runtime.cancel(claimed.id)
        self.db.commit()
        self.assertEqual(claimed.status, "CANCELLED")

    def test_precheck_fails_without_profile(self):
        self.profile.bound_account_id = None
        self.profile.account_id = None
        execution = create_execution_task_from_scheduler(self.db, self.task)
        self.db.commit()
        execution.tge_profile_id = None
        run_precheck(self.db, execution)
        self.db.commit()
        self.assertEqual(execution.status, "FAILED")
        self.assertEqual(execution.error_code, "NO_TGE_PROFILE")


if __name__ == "__main__":
    unittest.main()
