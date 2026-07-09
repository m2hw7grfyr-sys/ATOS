import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AIGenerationLog, LLMProvider, Platform, Post, PromptTemplate
from app.services.ai import AIAnalysisService, ReplyGenerationService


class AIServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
        self.db.flush()
        self.db.add(
            LLMProvider(
                provider_name="Mock Provider",
                provider_type="mock",
                model_name="mock-v0.3",
                enabled=True,
                priority=100,
                is_mock=True,
            )
        )
        self.db.add(
            PromptTemplate(
                name="Analysis",
                template_type="analysis_prompt",
                content="Analyze {{title}} {{content}}",
                version="test",
            )
        )
        self.db.add(
            PromptTemplate(
                name="Reply",
                template_type="reply_prompt",
                tone="supportive",
                content="Reply to {{title}} with {{tone}}",
                version="test",
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


if __name__ == "__main__":
    unittest.main()
