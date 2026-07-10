import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AIGenerationLog, LLMProvider, Platform, Post, PromptTemplate, ProviderRouting
from app.services.ai_runtime import (
    AIRequest,
    AIRuntime,
    PromptContext,
    TASK_TYPE_ANALYSIS,
    TASK_TYPE_EMBEDDING,
    TASK_TYPE_REPLY,
)


class AIRuntimeTest(unittest.TestCase):
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
            use_for_analysis=True,
            use_for_reply=True,
            use_for_embedding=True,
        )
        self.db.add(provider)
        self.db.flush()
        self.db.add(
            ProviderRouting(
                name="Runtime Analysis Route",
                task_type=TASK_TYPE_ANALYSIS,
                preferred_provider_id=provider.id,
                fallback_provider_id=provider.id,
                enabled=True,
                priority=1,
            )
        )
        self.db.add(
            ProviderRouting(
                name="Runtime Reply Route",
                task_type=TASK_TYPE_REPLY,
                preferred_provider_id=provider.id,
                fallback_provider_id=provider.id,
                enabled=True,
                priority=1,
            )
        )
        self.db.add(
            PromptTemplate(
                name="Runtime Analysis Prompt",
                template_type="analysis_prompt",
                content="Analyze {{title}} {{content}}",
                version="runtime-test",
                enabled=True,
            )
        )
        self.db.add(
            PromptTemplate(
                name="Runtime Reply Prompt",
                template_type="reply_prompt",
                content="Reply to {{title}} with {{strategy}} {{tone}}",
                version="runtime-test",
                enabled=True,
            )
        )
        self.post = Post(
            platform_id=platform.id,
            title="Need a better focus routine",
            content="I keep losing momentum after lunch.",
            url="https://example.com/runtime-post",
        )
        self.db.add(self.post)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_runtime_generates_analysis_and_logs_metadata(self):
        response = AIRuntime(self.db).generate_analysis(
            AIRequest(
                request_id="analysis-test",
                task_type=TASK_TYPE_ANALYSIS,
                post_id=self.post.id,
                prompt_context=PromptContext(),
            )
        )
        self.assertTrue(response.success)
        self.assertEqual(response.generation_source, "MOCK")
        self.assertIsNotNone(response.json_content)

        log = self.db.scalar(select(AIGenerationLog).order_by(AIGenerationLog.id.desc()))
        self.assertEqual(log.task_type, TASK_TYPE_ANALYSIS)
        self.assertEqual(log.provider_type, "mock")
        self.assertIsNotNone(log.final_prompt_hash)
        self.assertGreaterEqual(log.latency_ms, 0)

    def test_runtime_generates_reply(self):
        response = AIRuntime(self.db).generate_reply(
            AIRequest(
                request_id="reply-test",
                task_type=TASK_TYPE_REPLY,
                post_id=self.post.id,
                strategy="PURE_HELP",
                prompt_context=PromptContext(strategy="PURE_HELP", tone="supportive"),
            )
        )
        self.assertTrue(response.success)
        self.assertEqual(response.generation_source, "MOCK")
        self.assertIn(self.post.title, response.content)

    def test_runtime_embedding_uses_mock_flow(self):
        response = AIRuntime(self.db).generate_embedding(
            AIRequest(
                request_id="embedding-test",
                task_type=TASK_TYPE_EMBEDDING,
                post_id=self.post.id,
            )
        )
        self.assertTrue(response.success)
        self.assertEqual(response.json_content["embedding_dimensions"], 0)
        self.assertTrue(response.json_content["mock"])


if __name__ == "__main__":
    unittest.main()
