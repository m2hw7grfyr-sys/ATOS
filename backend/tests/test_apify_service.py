import json
import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import CrawlLog, DataSource, Platform, Post
from app.services.apify import ApifyService, normalize_post


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeApify:
    def __call__(self, request, timeout=0):
        if "/runs?" in request.full_url:
            return FakeResponse(
                {
                    "data": {
                        "status": "SUCCEEDED",
                        "defaultDatasetId": "dataset-demo",
                    }
                }
            )
        if "/datasets/" in request.full_url:
            return FakeResponse(
                [
                    {
                        "id": "post-1",
                        "title": "First item",
                        "text": "First body",
                        "url": "https://example.com/posts/1",
                        "username": "alice",
                        "subreddit": "demo",
                        "createdAt": "2026-07-09T08:00:00Z",
                    },
                    {
                        "title": "Second item",
                        "description": "Second body",
                        "url": "https://example.com/posts/2",
                        "ownerUsername": "bob",
                    },
                ]
            )
        return FakeResponse({"data": {"name": "demo-actor"}})


class ApifyServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        platform = Platform(
            name="Reddit",
            slug="reddit",
            adapter_key="reddit",
        )
        self.db.add(platform)
        self.db.flush()
        self.source = DataSource(
            name="Test source",
            source_type="APIFY",
            platform_id=platform.id,
            adapter_key="apify",
            config={
                "actor_id": "owner/actor",
                "apify_token": "secret-token",
                "input_json": {"search": "demo"},
                "max_items": 10,
            },
        )
        self.db.add(self.source)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_normalizer_keeps_raw_json(self):
        raw = {"postId": "42", "caption": "Hello", "postUrl": "https://x.test/42"}
        item = normalize_post(raw)
        self.assertEqual(item.source_post_id, "42")
        self.assertEqual(item.content, "Hello")
        self.assertEqual(item.raw_json, raw)

    def test_run_inserts_then_deduplicates(self):
        service = ApifyService(self.db, opener=FakeApify())
        first = service.run(self.source)
        second = service.run(self.source)

        self.assertEqual(first.status, "SUCCEEDED")
        self.assertEqual(first.inserted_count, 2)
        self.assertEqual(second.inserted_count, 0)
        self.assertEqual(second.duplicate_count, 2)
        self.assertEqual(self.db.scalar(select(func.count(Post.id))), 2)
        self.assertEqual(self.db.scalar(select(func.count(CrawlLog.id))), 2)


if __name__ == "__main__":
    unittest.main()
