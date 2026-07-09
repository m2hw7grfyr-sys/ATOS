import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, AccountLimit, AccountWorkingWindow, Platform, TGEProfile


class AccountCenterModelTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(self.platform)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_account_limit_window_and_unique_tge_binding(self):
        account = Account(
            platform_id=self.platform.id,
            username="account_center_test",
            risk_status="LOW",
            status="ACTIVE",
        )
        self.db.add(account)
        self.db.flush()
        self.db.add(AccountLimit(account_id=account.id, reply_daily_limit=5))
        self.db.add(
            AccountWorkingWindow(
                account_id=account.id,
                day_of_week="MON",
                start_time="09:00",
                end_time="12:00",
                timezone="Asia/Shanghai",
            )
        )
        self.db.add(
            TGEProfile(
                platform_id=self.platform.id,
                bound_account_id=account.id,
                account_id=account.id,
                profile_name="Primary",
                tge_environment_id="env-primary",
                status="ACTIVE",
            )
        )
        self.db.commit()

        self.db.add(
            TGEProfile(
                platform_id=self.platform.id,
                bound_account_id=account.id,
                account_id=account.id,
                profile_name="Duplicate",
                tge_environment_id="env-duplicate",
                status="ACTIVE",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()


if __name__ == "__main__":
    unittest.main()
