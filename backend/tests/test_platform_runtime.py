import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import PlatformRegistry
from app.services.platform_runtime import PlatformCapabilityError, PlatformRuntime


class PlatformRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_discovers_known_platform_adapters(self):
        discovered = PlatformRuntime(self.db).discover()
        names = {item["platform_name"] for item in discovered}
        self.assertIn("reddit", names)
        self.assertIn("x", names)
        self.assertIn("facebook", names)
        self.assertIn("instagram", names)
        self.assertIn("tiktok", names)

    def test_capability_check_accepts_reddit_reply_and_rejects_tiktok_reply(self):
        runtime = PlatformRuntime(self.db)

        reddit = runtime.check_capability("reddit", "PREPARE_REPLY")
        self.assertTrue(reddit["supported"])
        self.assertEqual(reddit["capability_required"], "REPLY")

        tiktok = runtime.check_capability("tiktok", "PREPARE_REPLY")
        self.assertFalse(tiktok["supported"])
        self.assertEqual(tiktok["capability_required"], "REPLY")

        with self.assertRaises(PlatformCapabilityError):
            runtime.assert_capability("tiktok", "PREPARE_REPLY")

    def test_health_updates_platform_registry(self):
        runtime = PlatformRuntime(self.db)
        health_rows = runtime.health()
        self.db.commit()

        self.assertGreaterEqual(len(health_rows), 5)
        reddit = self.db.scalar(
            select(PlatformRegistry).where(PlatformRegistry.platform_name == "reddit")
        )
        self.assertIsNotNone(reddit)
        self.assertEqual(reddit.status, "HEALTHY")
        self.assertEqual(reddit.adapter_name, "RedditAdapter")
        self.assertTrue(reddit.capabilities["REPLY"])


if __name__ == "__main__":
    unittest.main()
