import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Platform, Post, Reply, ReplyTask, ReplyTemplate
from app.services.reply_template_strategy import TemplateSelectionEngine, ensure_reply_template_seed


class ReplyTemplateStrategyTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.reddit = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.x = Platform(name="X", slug="x", adapter_key="x")
        self.db.add_all([self.reddit, self.x])
        self.db.flush()
        self.reddit_post = Post(
            platform_id=self.reddit.id,
            title="Need help staying organized",
            content="I keep losing track of my day.",
            url="https://example.com/reddit-post",
        )
        self.x_post = Post(
            platform_id=self.x.id,
            title="Focus stack ideas?",
            content="Looking for a better workflow.",
            url="https://example.com/x-post",
        )
        self.db.add_all([self.reddit_post, self.x_post])
        self.db.flush()
        self.reddit_reply = Reply(post_id=self.reddit_post.id, content="Reddit reply")
        self.x_reply = Reply(post_id=self.x_post.id, content="X reply")
        self.db.add_all([self.reddit_reply, self.x_reply])
        self.db.commit()
        ensure_reply_template_seed(self.db)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def template(self, intent: str) -> ReplyTemplate:
        template = self.db.scalar(select(ReplyTemplate).where(ReplyTemplate.funnel_intent == intent))
        self.assertIsNotNone(template)
        return template

    def test_seed_creates_five_chinese_templates(self):
        templates = self.db.scalars(select(ReplyTemplate)).all()
        self.assertEqual(len(templates), 5)
        self.assertIn("纯帮助，不引流", {template.name_cn for template in templates})
        self.assertIn("直接外链", {template.name_cn for template in templates})

    def test_reddit_direct_link_is_blocked_by_platform_guard(self):
        direct_link = self.template("DIRECT_LINK_CTA")
        task = ReplyTask(
            post_id=self.reddit_post.id,
            reply_id=self.reddit_reply.id,
            platform="reddit",
            reply_content="Helpful answer with a direct link.",
            status="APPROVED",
            reply_template_id=direct_link.id,
            funnel_intent=direct_link.funnel_intent,
        )
        self.db.add(task)
        self.db.flush()

        allowed, reason = TemplateSelectionEngine(self.db).validate_approval(task)

        self.assertFalse(allowed)
        self.assertIn("Platform rule", reason)

    def test_x_main_account_template_is_allowed(self):
        main_account = self.template("MAIN_ACCOUNT_CTA")
        selection = TemplateSelectionEngine(self.db).select(
            platform="x",
            post_score=90,
            risk_score=5,
            operator_preference=main_account.id,
        )
        task = ReplyTask(
            post_id=self.x_post.id,
            reply_id=self.x_reply.id,
            platform="x",
            reply_content="Helpful answer with a thread mention.",
            status="APPROVED",
        )
        self.db.add(task)
        self.db.flush()
        TemplateSelectionEngine(self.db).apply_to_reply_task(task, selection)

        allowed, reason = TemplateSelectionEngine(self.db).validate_approval(task)

        self.assertTrue(allowed, reason)
        self.assertEqual(task.funnel_intent, "MAIN_ACCOUNT_CTA")

    def test_high_risk_template_is_not_auto_assisted(self):
        direct_link = self.template("DIRECT_LINK_CTA")
        task = ReplyTask(
            post_id=self.x_post.id,
            reply_id=self.x_reply.id,
            platform="x",
            reply_content="Helpful answer with direct link.",
            status="APPROVED",
            reply_template_id=direct_link.id,
            funnel_intent=direct_link.funnel_intent,
        )
        self.db.add(task)
        self.db.flush()

        allowed, reason = TemplateSelectionEngine(self.db).auto_assisted_allowed(task)

        self.assertFalse(allowed)
        self.assertIn("High-risk", reason)


if __name__ == "__main__":
    unittest.main()
