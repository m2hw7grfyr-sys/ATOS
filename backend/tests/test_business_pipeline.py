import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    AITask,
    AuditLog,
    BusinessEvent,
    LLMProvider,
    Platform,
    Post,
    PostTimeline,
    PromptTemplate,
    ProviderRouting,
    Reply,
    SchedulerTask,
)
from app.services.pipeline import BusinessPipelineService


class BusinessPipelineTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(self.platform)
        self.db.flush()
        provider = LLMProvider(
            provider_name="Mock Provider",
            provider_type="mock",
            model_name="mock-v0.3",
            enabled=True,
            priority=100,
            is_mock=True,
        )
        self.db.add(provider)
        self.db.flush()
        self.db.add(
            ProviderRouting(
                name="Pipeline Analysis Route",
                task_type="ANALYSIS",
                preferred_provider_id=provider.id,
                fallback_provider_id=provider.id,
                enabled=True,
                priority=1,
            )
        )
        self.db.add(
            ProviderRouting(
                name="Pipeline Reply Route",
                task_type="REPLY",
                preferred_provider_id=provider.id,
                fallback_provider_id=provider.id,
                enabled=True,
                priority=1,
            )
        )
        self.db.add(
            PromptTemplate(
                name="Pipeline Analysis",
                template_type="analysis_prompt",
                content="Analyze {{title}}",
                version="test",
            )
        )
        self.db.add(
            PromptTemplate(
                name="Pipeline Reply",
                template_type="reply_prompt",
                content="Reply to {{title}} using {{strategy}}",
                version="test",
            )
        )
        self.post = Post(
            platform_id=self.platform.id,
            title="Need a better routine",
            content="I need a small next step.",
            url="https://example.com/pipeline",
            status="NEW",
        )
        self.db.add(self.post)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_pipeline_analyze_approve_and_schedule(self):
        service = BusinessPipelineService(self.db, actor="test", trace_id="test-trace")
        analysis = service.analyze_post(self.post.id)
        self.assertEqual(analysis["status"], "WAITING_REVIEW")
        self.assertIsNotNone(analysis["reply_id"])

        approved = service.approve_post(self.post.id)
        self.assertEqual(approved["status"], "APPROVED")

        scheduled = service.send_to_scheduler(self.post.id)
        self.assertEqual(scheduled["status"], "SCHEDULED")

        task = self.db.scalar(select(AITask).where(AITask.post_id == self.post.id))
        reply = self.db.scalar(select(Reply).where(Reply.post_id == self.post.id))
        scheduler = self.db.scalar(select(SchedulerTask).where(SchedulerTask.post_id == self.post.id))
        self.assertEqual(task.status, "APPROVED")
        self.assertEqual(reply.status, "APPROVED")
        self.assertEqual(scheduler.ai_task_id, task.id)
        self.assertEqual(scheduler.source, "PIPELINE")

        self.assertGreaterEqual(len(self.db.scalars(select(PostTimeline)).all()), 6)
        self.assertGreaterEqual(len(self.db.scalars(select(BusinessEvent)).all()), 5)
        self.assertGreaterEqual(len(self.db.scalars(select(AuditLog)).all()), 2)


if __name__ == "__main__":
    unittest.main()
