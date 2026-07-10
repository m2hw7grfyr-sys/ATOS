import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, ExecutionTask, IntelligenceRecommendation, Platform, Post, Reply, ReplySimilarity
from app.services.intelligence_runtime import IntelligenceRuntime


class IntelligenceRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
        self.db.flush()
        account = Account(platform_id=platform.id, username="intel-account", status="ACTIVE")
        post = Post(
            platform_id=platform.id,
            source_post_id="intel-post",
            url_hash="intel-post",
            title="Need a better focus workflow",
            content="I keep losing track of tasks during work.",
            url="https://example.com/intel",
            score=12,
            comment_count=4,
            raw_json={"seed": True},
        )
        self.db.add_all([account, post])
        self.db.flush()
        self.reply = Reply(post_id=post.id, content="I would start with one visible list and a five minute reset between tasks.", status="APPROVED")
        self.reply_2 = Reply(post_id=post.id, content="Start with one visible list and a five minute reset between tasks.", status="APPROVED")
        self.db.add_all([self.reply, self.reply_2])
        self.db.flush()
        self.db.add(
            ExecutionTask(
                account_id=account.id,
                platform="reddit",
                action_type="PREPARE_REPLY",
                payload_json={"strategy": "SEMI_AUTO"},
                status="SUCCESS",
                queue_status="SUCCESS",
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_collect_performance_scores_and_recommends(self):
        runtime = IntelligenceRuntime(self.db)
        dashboard = runtime.collect_performance()
        self.db.commit()

        self.assertGreaterEqual(len(dashboard["top_replies"]), 1)
        self.assertIn("funnel", dashboard)
        recommendation = self.db.scalar(select(IntelligenceRecommendation))
        self.assertIsNotNone(recommendation)

    def test_score_reply_and_similarity_detection(self):
        runtime = IntelligenceRuntime(self.db)
        score = runtime.score_reply(self.reply.id)
        similarities = runtime.detect_duplicate_replies(threshold=70)
        self.db.commit()

        self.assertGreater(score.score, 0)
        self.assertGreaterEqual(len(similarities), 1)
        stored = self.db.scalar(select(ReplySimilarity))
        self.assertIsNotNone(stored)


if __name__ == "__main__":
    unittest.main()
