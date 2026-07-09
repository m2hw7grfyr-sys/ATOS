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
    StatisticSnapshot,
    SystemSetting,
    TGEProfile,
)


SEED_VERSION = "v0.1-acceptance"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        marker = db.scalar(
            select(SystemSetting).where(SystemSetting.key == "seed.version")
        )
        if marker and marker.value.get("version") == SEED_VERSION:
            print(f"Seed already applied: {SEED_VERSION}")
            return

        platforms = {}
        for name, slug, status in [
            ("Reddit", "reddit", "ACTIVE"),
            ("X", "x", "PLANNED"),
            ("Facebook", "facebook", "PLANNED"),
        ]:
            item = db.scalar(select(Platform).where(Platform.slug == slug))
            if not item:
                item = Platform(
                    name=name,
                    slug=slug,
                    adapter_key=slug,
                    status=status,
                )
                db.add(item)
                db.flush()
            platforms[slug] = item

        source_specs = [
            (
                "Apify Reddit Discovery",
                platforms["reddit"].id,
                "demo/reddit-discovery",
            ),
            (
                "Apify Multi-platform Search",
                platforms["x"].id,
                "demo/social-search",
            ),
        ]
        sources = []
        for name, platform_id, actor_id in source_specs:
            item = db.scalar(select(DataSource).where(DataSource.name == name))
            if not item:
                item = DataSource(
                    name=name,
                    source_type="APIFY",
                    platform_id=platform_id,
                    adapter_key="apify",
                    config={
                        "actor_id": actor_id,
                        "workspace": "local-demo",
                        "token_configured": False,
                    },
                    status="READY",
                )
                db.add(item)
                db.flush()
            sources.append(item)

        now = datetime.now(timezone.utc)
        post_specs = [
            ("reddit", 0, "ADHD", "focus_builder", "How do you keep a routine when every day feels different?", "I have tried several planners but stop using them after a week.", ["routine", "question"], "ANALYZED"),
            ("reddit", 0, "productivity", "workflow_notes", "Looking for a calmer way to manage recurring tasks", "Most tools feel too complicated for my small team.", ["workflow", "purchase_intent"], "NEW"),
            ("reddit", 0, "SaaS", "founder_weekly", "What did you automate first in your SaaS operations?", "Curious which repetitive process gave you the fastest return.", ["saas", "discussion"], "QUALIFIED"),
            ("reddit", 0, "ADHD", "day_by_day", "A lightweight weekly review that finally worked", "Sharing a small routine that has been sustainable for me.", ["experience", "routine"], "ANALYZED"),
            ("x", 1, "builders", "ship_small", "What is your smallest useful automation?", "Collecting examples of practical local-first workflows.", ["automation", "question"], "NEW"),
            ("x", 1, "founders", "quiet_ops", "Operational dashboards should reduce decisions", "A good dashboard makes the next action obvious.", ["dashboard", "operations"], "QUALIFIED"),
            ("x", 1, "ai-tools", "model_router", "Local models for classification tasks", "Small models can be effective when the output schema is constrained.", ["local_llm", "ai"], "ANALYZED"),
            ("facebook", 1, "Small Business Systems", "ops_owner", "How do small teams track recurring work?", "We need something simple enough to maintain every day.", ["small_business", "workflow"], "NEW"),
            ("facebook", 1, "Productivity Community", "weekly_reset", "A simple planning ritual for Monday mornings", "This checklist helped our team start the week with less noise.", ["planning", "experience"], "QUALIFIED"),
            ("facebook", 1, "SaaS Operators", "metric_maker", "Which metric belongs on the first dashboard?", "I am deciding between queue health and conversion metrics.", ["metrics", "dashboard"], "ANALYZED"),
        ]
        posts = []
        for index, spec in enumerate(post_specs, start=1):
            platform_slug, source_index, community, author, title, content, tags, status = spec
            source_post_id = f"seed-{index:03d}"
            item = db.scalar(
                select(Post).where(Post.source_post_id == source_post_id)
            )
            if not item:
                item = Post(
                    platform_id=platforms[platform_slug].id,
                    data_source_id=sources[source_index].id,
                    source_post_id=source_post_id,
                    community=community,
                    author=author,
                    title=title,
                    content=content,
                    url=f"https://example.com/{platform_slug}/{source_post_id}",
                    tags=tags,
                    published_at=now - timedelta(hours=index * 2),
                    status=status,
                )
                db.add(item)
                db.flush()
            posts.append(item)

        ai_tasks = []
        ai_specs = [
            (posts[0], "EDUCATION", 74, 18, "REVIEWING"),
            (posts[1], "PURE_HELP", 81, 12, "APPROVED"),
            (posts[2], "EXPERIENCE", 69, 16, "APPROVED"),
        ]
        for index, (post, strategy, commercial, risk, task_status) in enumerate(
            ai_specs, start=1
        ):
            task = db.scalar(
                select(AITask).where(
                    AITask.post_id == post.id,
                    AITask.provider == "mock-seed",
                )
            )
            if not task:
                task = AITask(
                    post_id=post.id,
                    provider="mock-seed",
                    model="mock-v0.1",
                    strategy=strategy,
                    commercial_score=commercial,
                    risk_score=risk,
                    result={
                        "intent": ["QUESTION", "SUPPORT"],
                        "confidence": round(0.8 + index * 0.04, 2),
                        "seed": True,
                    },
                    status=task_status,
                )
                db.add(task)
                db.flush()
            reply = db.scalar(select(Reply).where(Reply.ai_task_id == task.id))
            if not reply:
                reply = Reply(
                    post_id=post.id,
                    ai_task_id=task.id,
                    content=(
                        f"Seed draft {index}: Start with one small, repeatable step "
                        "and review the result before adding more complexity."
                    ),
                    source="MOCK_PROVIDER",
                    status="APPROVED" if task_status == "APPROVED" else "GENERATED",
                )
                db.add(reply)
                db.flush()
            ai_tasks.append((task, reply))

        account_specs = [
            ("reddit", "atos_reddit_demo", "ATOS Reddit Demo", 92),
            ("x", "atos_x_demo", "ATOS X Demo", 88),
            ("facebook", "atos_facebook_demo", "ATOS Facebook Demo", 85),
        ]
        accounts = []
        for platform_slug, username, display_name, health_score in account_specs:
            item = db.scalar(select(Account).where(Account.username == username))
            if not item:
                item = Account(
                    platform_id=platforms[platform_slug].id,
                    username=username,
                    display_name=display_name,
                    health_score=health_score,
                    daily_limits={"browse": 20, "reply": 5, "like": 8},
                    working_time={
                        "timezone": "Asia/Shanghai",
                        "ranges": ["09:00-12:00", "19:00-22:00"],
                    },
                    status="ACTIVE",
                )
                db.add(item)
                db.flush()
            accounts.append(item)

        for account, environment_id in zip(
            accounts[:2], ["tge-demo-001", "tge-demo-002"]
        ):
            profile = db.scalar(
                select(TGEProfile).where(TGEProfile.account_id == account.id)
            )
            if not profile:
                db.add(
                    TGEProfile(
                        account_id=account.id,
                        environment_id=environment_id,
                        name=f"{account.display_name} Environment",
                        api_base_url="http://127.0.0.1:50326",
                        status="OFFLINE",
                    )
                )

        scheduler_specs = [
            ("REPLY", accounts[0], posts[1], ai_tasks[1][1], "HIGH"),
            ("REPLY", accounts[1], posts[2], ai_tasks[2][1], "MEDIUM"),
            ("BROWSE", accounts[2], posts[7], None, "LOW"),
        ]
        for index, (task_type, account, post, reply, priority) in enumerate(
            scheduler_specs, start=1
        ):
            item = db.scalar(
                select(SchedulerTask).where(
                    SchedulerTask.task_type == task_type,
                    SchedulerTask.account_id == account.id,
                    SchedulerTask.post_id == post.id,
                )
            )
            if not item:
                db.add(
                    SchedulerTask(
                        task_type=task_type,
                        platform_id=account.platform_id,
                        account_id=account.id,
                        post_id=post.id,
                        reply_id=reply.id if reply else None,
                        priority=priority,
                        scheduled_at=now + timedelta(minutes=index * 15),
                        payload={
                            "mode": "HUMAN_IN_THE_LOOP",
                            "seed": True,
                        },
                        status="QUEUED",
                    )
                )

        setting_specs = [
            ("ai.default_provider", "AI", {"provider": "mock", "model": "mock-v0.1"}, False),
            ("scheduler.defaults", "SCHEDULER", {"random_delay": False, "min_delay": 120, "max_delay": 480}, False),
            ("execution.tge", "EXECUTION", {"base_url": "http://127.0.0.1:50326", "enabled": False}, False),
            ("data.apify", "DATA_CENTER", {"enabled": False}, True),
        ]
        for key, category, value, is_secret in setting_specs:
            item = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
            if not item:
                db.add(
                    SystemSetting(
                        key=key,
                        category=category,
                        value=value,
                        is_secret=is_secret,
                    )
                )

        for metric, dimension, value in [
            ("imported_posts", "SYSTEM", 10),
            ("ai_tasks", "SYSTEM", 3),
            ("scheduler_queue", "SYSTEM", 3),
            ("active_accounts", "SYSTEM", 3),
            ("reply_success_rate", "REDDIT", 92),
            ("average_risk_score", "SYSTEM", 15.3),
        ]:
            item = db.scalar(
                select(StatisticSnapshot).where(
                    StatisticSnapshot.metric == metric,
                    StatisticSnapshot.dimension == dimension,
                    StatisticSnapshot.period == "TODAY",
                )
            )
            if not item:
                db.add(
                    StatisticSnapshot(
                        metric=metric,
                        dimension=dimension,
                        value=value,
                        period="TODAY",
                        metadata_json={"seed": True},
                    )
                )

        if marker:
            marker.value = {"version": SEED_VERSION}
        else:
            db.add(
                SystemSetting(
                    key="seed.version",
                    category="SYSTEM",
                    value={"version": SEED_VERSION},
                )
            )
        db.commit()
        print(
            "ATOS acceptance seed ready: 3 platforms, 2 data sources, "
            "10 posts, 3 AI tasks, 3 scheduler tasks, 3 accounts, "
            "2 TGE profiles, 6 statistics."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
