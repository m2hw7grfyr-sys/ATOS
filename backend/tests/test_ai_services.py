import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AIGenerationLog, LLMProvider, Platform, Post, PromptTemplate, PromptVersion, ProviderRouting
from app.services.ai import AIAnalysisService, ReplyGenerationService, preview_prompt


class AIServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
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
        self.analysis_template = PromptTemplate(
            name="Analysis",
            template_type="analysis_prompt",
            content="Analyze {{title}} {{content}}",
            version="test",
        )
        self.reply_template = PromptTemplate(
            name="Reply",
            template_type="reply_prompt",
            tone="supportive",
            content="Reply to {{title}} with {{tone}}",
            version="test",
        )
        self.db.add(self.analysis_template)
        self.db.add(self.reply_template)
        self.db.flush()
        self.db.add(
            PromptVersion(
                prompt_template_id=self.reply_template.id,
                version="v1.2-test",
                content="Versioned reply for {{title}} using {{strategy}} and {{tone}}",
                variables_schema={"title": "string"},
                tone="supportive",
                enabled=True,
                is_default=True,
            )
        )
        self.db.add(
            ProviderRouting(
                name="Mock Reply Route",
                task_type="REPLY",
                preferred_provider_id=provider.id,
                fallback_provider_id=provider.id,
                enabled=True,
                priority=1,
            )
        )
        self.db.add(
            ProviderRouting(
                name="Mock Analysis Route",
                task_type="ANALYSIS",
                preferred_provider_id=provider.id,
                fallback_provider_id=provider.id,
                enabled=True,
                priority=1,
            )
        )
        self.post = Post(
            platform_id=platform.id,
            title="How do I keep a routine?",
            content="I stop after a week.",
            url="https://example.com/post",
        )
        self.db.add(self.post)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_mock_analysis_and_reply_generation(self):
        analysis = AIAnalysisService().analyze(self.db, self.post.id)
        self.assertEqual(analysis["task"].status, "ANALYZED")
        self.assertEqual(analysis["analysis"].generation_source, "MOCK")

        reply = ReplyGenerationService().generate(
            self.db,
            post_id=self.post.id,
            strategy="PURE_HELP",
            tone="supportive",
            variables={},
        )
        self.assertEqual(reply["task"].status, "GENERATED")
        self.assertEqual(reply["reply"].source, "MOCK")

        logs = self.db.scalars(select(AIGenerationLog)).all()
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log.total_tokens > 0 for log in logs))

    def test_prompt_preview_uses_prompt_version(self):
        task = AIAnalysisService().analyze(self.db, self.post.id)["task"]
        preview = preview_prompt(
            self.db,
            task_id=task.id,
            strategy="PURE_HELP",
            tone="supportive",
            variables={},
        )
        self.assertEqual(preview["prompt_version"], "v1.2-test")
        self.assertIn("Versioned reply", preview["final_prompt"])

    def test_invalid_real_provider_falls_back_to_mock_and_logs_reason(self):
        bad_provider = LLMProvider(
            provider_name="Broken OpenAI",
            provider_type="openai",
            model_name="gpt-test",
            enabled=True,
            priority=1,
            is_mock=False,
            use_for_analysis=True,
            use_for_reply=True,
        )
        self.db.add(bad_provider)
        self.db.flush()
        route = self.db.scalar(select(ProviderRouting).where(ProviderRouting.name == "Mock Reply Route"))
        route.preferred_provider_id = bad_provider.id
        self.db.commit()

        reply = ReplyGenerationService().generate(
            self.db,
            post_id=self.post.id,
            strategy="PURE_HELP",
            tone="supportive",
            variables={},
        )
        self.assertTrue(reply["fallback_used"])
        log = self.db.scalar(
            select(AIGenerationLog)
            .where(AIGenerationLog.fallback_used.is_(True), AIGenerationLog.status == "SUCCESS")
            .order_by(AIGenerationLog.id.desc())
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.fallback_to_provider, "Mock Provider")
        self.assertIn("api_key", log.fallback_reason)


if __name__ == "__main__":
    unittest.main()
