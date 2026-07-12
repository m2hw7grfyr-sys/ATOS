import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import studio as studio_api
from app.database import Base
from app.models import Platform, Post
from app.schemas import StudioPushBatchRequest
from app.services.studio_client import StudioAuthError, StudioUnavailableError


class FakeStudioClient:
    next_result = {
        "created": True,
        "duplicate": False,
        "studio_item_id": "studio-1",
        "status": "pending_review",
        "source_type": "atos_manual_push",
    }
    error = None
    payloads = []

    def __init__(self):
        pass

    def push_content_item(self, payload):
        self.__class__.payloads.append(payload)
        if self.__class__.error:
            raise self.__class__.error
        return dict(self.__class__.next_result)


class StudioPushTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(platform)
        self.db.flush()
        self.post = Post(
            platform_id=platform.id,
            source_post_id="abc123",
            title="Real database title",
            content="Real database body",
            url="https://example.com/abc123",
            author="author-a",
            score=88,
            comment_count=42,
            status="NEW",
        )
        self.db.add(self.post)
        self.db.commit()
        FakeStudioClient.next_result = {
            "created": True,
            "duplicate": False,
            "studio_item_id": "studio-1",
            "status": "pending_review",
            "source_type": "atos_manual_push",
        }
        FakeStudioClient.error = None
        FakeStudioClient.payloads = []

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def test_single_push_success_uses_database_post(self):
        with patch("app.api.studio.StudioClient", FakeStudioClient):
            result = studio_api._push_post_to_studio(
                self.db,
                atos_post_id=str(self.post.id),
                requested_content_type="video",
                target_platforms=["tiktok"],
                operator_note="note",
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["created"])
        self.assertEqual(FakeStudioClient.payloads[0]["title"], "Real database title")
        self.assertEqual(FakeStudioClient.payloads[0]["body"], "Real database body")

    def test_single_push_duplicate(self):
        FakeStudioClient.next_result = {
            "created": False,
            "duplicate": True,
            "studio_item_id": "studio-1",
            "status": "pending_review",
            "source_type": "atos_manual_push",
        }
        with patch("app.api.studio.StudioClient", FakeStudioClient):
            result = studio_api._push_post_to_studio(
                self.db,
                atos_post_id=str(self.post.id),
                requested_content_type="video",
                target_platforms=["tiktok"],
                operator_note="note",
            )
        self.assertTrue(result["duplicate"])

    def test_studio_unavailable_and_auth_failure_surface(self):
        FakeStudioClient.error = StudioUnavailableError("down")
        with patch("app.api.studio.StudioClient", FakeStudioClient):
            with self.assertRaises(StudioUnavailableError):
                studio_api._push_post_to_studio(
                    self.db,
                    atos_post_id=str(self.post.id),
                    requested_content_type="video",
                    target_platforms=["tiktok"],
                    operator_note="note",
                )
        FakeStudioClient.error = StudioAuthError("auth")
        with patch("app.api.studio.StudioClient", FakeStudioClient):
            with self.assertRaises(StudioAuthError):
                studio_api._push_post_to_studio(
                    self.db,
                    atos_post_id=str(self.post.id),
                    requested_content_type="video",
                    target_platforms=["tiktok"],
                    operator_note="note",
                )

    def test_post_not_found(self):
        with self.assertRaises(Exception):
            studio_api._push_post_to_studio(
                self.db,
                atos_post_id="999",
                requested_content_type="video",
                target_platforms=["tiktok"],
                operator_note="note",
            )

    def test_batch_limit_validation(self):
        with self.assertRaises(ValidationError):
            StudioPushBatchRequest(
                atos_post_ids=[str(i) for i in range(51)],
                requested_content_type="video",
                target_platforms=["tiktok"],
                operator_note="",
            )

    def test_batch_partial_success(self):
        request = SimpleNamespace(state=SimpleNamespace(trace_id="test-trace"))
        payload = StudioPushBatchRequest(
            atos_post_ids=[str(self.post.id), "999"],
            requested_content_type="video",
            target_platforms=["tiktok"],
            operator_note="batch",
        )
        with patch("app.api.studio.StudioClient", FakeStudioClient):
            result = studio_api.push_posts_to_studio_batch(payload, request, self.db)

        self.assertEqual(result["data"]["total"], 2)
        self.assertEqual(result["data"]["created"], 1)
        self.assertEqual(result["data"]["failed"], 1)


if __name__ == "__main__":
    unittest.main()
