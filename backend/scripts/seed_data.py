from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import (
    AITask,
    Account,
    DataSource,
    Platform,
    Post,
    Reply,
    SchedulerTask,
    SystemSetting,
    TGEProfile,
)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Platform.id).limit(1)):
            print("Seed skipped: data already exists.")
            return

        reddit = Platform(name="Reddit", slug="reddit", adapter_key="reddit")
        x_platform = Platform(name="X", slug="x", adapter_key="x", status="PLANNED")
        facebook = Platform(
            name="Facebook", slug="facebook", adapter_key="facebook", status="PLANNED"
        )
        db.add_all([reddit, x_platform, facebook])
        db.flush()

        source = DataSource(
            name="Apify Reddit Discovery",
            source_type="APIFY",
            platform_id=reddit.id,
            adapter_key="apify",
            config={
                "actor_id": "demo/reddit-scraper",
                "workspace": "local-demo",
                "token_configured": False,
            },
            status="READY",
        )
        db.add(source)
        db.flush()

        now = datetime.now(timezone.utc)
        posts = [
            Post(
                platform_id=reddit.id,
                data_source_id=source.id,
                source_post_id="demo-001",
                community="ADHD",
                author="focus_builder",
                title="How do you keep a routine when every day feels different?",
                content="I have tried several planners but stop using them after a week.",
                url="https://www.reddit.com/r/ADHD/",
                tags=["routine", "question"],
                published_at=now - timedelta(hours=2),
                status="ANALYZED",
            ),
            Post(
                platform_id=reddit.id,
                data_source_id=source.id,
                source_post_id="demo-002",
                community="productivity",
                author="workflow_notes",
                title="Looking for a calmer way to manage recurring tasks",
                content="Most tools feel too complicated for my small team.",
                url="https://www.reddit.com/r/productivity/",
                tags=["workflow", "purchase_intent"],
                published_at=now - timedelta(hours=5),
                status="NEW",
            ),
            Post(
                platform_id=reddit.id,
                data_source_id=source.id,
                source_post_id="demo-003",
                community="SaaS",
                author="founder_weekly",
                title="What did you automate first in your SaaS operations?",
                content="Curious which repetitive process gave you the fastest return.",
                url="https://www.reddit.com/r/SaaS/",
                tags=["saas", "discussion"],
                published_at=now - timedelta(days=1),
                status="QUALIFIED",
            ),
        ]
        db.add_all(posts)
        db.flush()

        ai_task = AITask(
            post_id=posts[0].id,
            provider="ollama",
            model="llama3.1:8b",
            strategy="EDUCATION",
            commercial_score=74,
            risk_score=18,
            result={"intent": ["QUESTION", "SUPPORT"], "confidence": 0.88},
            status="REVIEWING",
        )
        db.add(ai_task)
        db.flush()

        reply = Reply(
            post_id=posts[0].id,
            ai_task_id=ai_task.id,
            content=(
                "A smaller routine may be easier to keep than a perfect system. "
                "I would start with one daily anchor and review it weekly."
            ),
            status="APPROVED",
        )
        account = Account(
            platform_id=reddit.id,
            username="atos_demo_operator",
            display_name="ATOS Demo",
            health_score=92,
            daily_limits={"browse": 20, "reply": 5, "like": 8},
            working_time={"timezone": "Asia/Shanghai", "ranges": ["09:00-12:00", "19:00-22:00"]},
        )
        db.add_all([reply, account])
        db.flush()

        db.add(
            TGEProfile(
                account_id=account.id,
                environment_id="configure-me",
                name="Demo environment",
                api_base_url="http://127.0.0.1:50326",
                status="OFFLINE",
            )
        )
        db.add(
            SchedulerTask(
                task_type="REPLY",
                platform_id=reddit.id,
                account_id=account.id,
                post_id=posts[0].id,
                reply_id=reply.id,
                priority="HIGH",
                scheduled_at=now + timedelta(minutes=15),
                payload={"mode": "HUMAN_IN_THE_LOOP"},
                status="QUEUED",
            )
        )
        db.add_all(
            [
                SystemSetting(
                    key="ai.default_provider",
                    category="AI",
                    value={"provider": "ollama", "model": "llama3.1:8b"},
                ),
                SystemSetting(
                    key="scheduler.defaults",
                    category="SCHEDULER",
                    value={"random_delay": False, "min_delay": 120, "max_delay": 480},
                ),
                SystemSetting(
                    key="execution.tge",
                    category="EXECUTION",
                    value={"base_url": "http://127.0.0.1:50326", "enabled": False},
                ),
                SystemSetting(
                    key="data.apify",
                    category="DATA_CENTER",
                    value={"enabled": False},
                    is_secret=True,
                ),
            ]
        )
        db.commit()
        print("ATOS demo data created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
