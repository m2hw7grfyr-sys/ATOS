import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, ExecutionTask, Platform, SchedulerTask, TGEProfile
from app.services.execution import create_execution_task_from_scheduler, run_precheck


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
        self.assertEqual(execution.status, "RECEIVED")
        run_precheck(self.db, execution)
        self.db.commit()
        self.assertEqual(execution.status, "ENVIRONMENT_READY")
        self.assertEqual(execution.precheck_status, "SUCCESS")
        self.assertEqual(self.db.scalar(select(ExecutionTask)).id, execution.id)

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
