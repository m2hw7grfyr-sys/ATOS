import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Platform, Post


class StudioApiTest(unittest.TestCase):
    def setUp(self):
        os.environ["ATOS_STUDIO_AUTH_ENABLED"] = "true"
        os.environ["ATOS_STUDIO_API_TOKEN"] = "test-studio-token"
        get_settings.cache_clear()
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.platform = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        self.db.add(self.platform)
        self.db.flush()
        self.post = Post(
            platform_id=self.platform.id,
            source_post_id="abc123",
            title="Studio candidate",
            content="Useful source text",
            url="https://example.com/abc123",
            author="author-a",
            score=42,
            comment_count=7,
            tags=["studio"],
            status="NEW",
        )
        self.second_post = Post(
            platform_id=self.platform.id,
            source_post_id="def456",
            title="Second candidate",
            content="More text",
            url="https://example.com/def456",
            author="author-b",
            score=5,
            comment_count=1,
        )
        self.db.add_all([self.post, self.second_post])
        self.db.commit()

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        get_settings.cache_clear()
        os.environ.pop("ATOS_STUDIO_AUTH_ENABLED", None)
        os.environ.pop("ATOS_STUDIO_API_TOKEN", None)

    def auth_headers(self, token="test-studio-token"):
        return {"Authorization": f"Bearer {token}"}

    def response_data(self, response):
        return response.json()["data"]

    def test_health_requires_and_accepts_token(self):
        missing = self.client.get("/api/studio/health")
        wrong = self.client.get("/api/studio/health", headers=self.auth_headers("wrong"))
        ok = self.client.get("/api/studio/health", headers=self.auth_headers())

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.response_data(ok)["service"], "atos-studio-api")

    def test_list_returns_data_with_limit_and_offset(self):
        response = self.client.get(
            "/api/studio/content-items?limit=1&offset=1",
            headers=self.auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        data = self.response_data(response)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["limit"], 1)
        self.assertEqual(data["offset"], 1)
        self.assertEqual(len(data["items"]), 1)

    def test_limit_upper_bound_is_enforced(self):
        response = self.client.get("/api/studio/content-items?limit=201", headers=self.auth_headers())
        self.assertEqual(response.status_code, 422)

    def test_get_by_source_post_id_and_missing_404(self):
        response = self.client.get("/api/studio/content-items/abc123", headers=self.auth_headers())
        missing = self.client.get("/api/studio/content-items/not-found", headers=self.auth_headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.response_data(response)["source_post_id"], "abc123")
        self.assertEqual(missing.status_code, 404)

    def test_invalid_query_parameter_returns_422(self):
        response = self.client.get("/api/studio/content-items?offset=-1", headers=self.auth_headers())
        self.assertEqual(response.status_code, 422)

    def test_read_only_api_does_not_modify_posts(self):
        before = self.db.scalar(select(Post.status).where(Post.id == self.post.id))
        self.client.get("/api/studio/content-items", headers=self.auth_headers())
        self.client.get("/api/studio/content-items/abc123", headers=self.auth_headers())
        self.db.expire_all()
        after = self.db.scalar(select(Post.status).where(Post.id == self.post.id))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
