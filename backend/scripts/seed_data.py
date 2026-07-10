import hashlib
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.models import (
    AIAnalysisResult,
    AITask,
    Account,
    AccountLimit,
    AccountWorkingWindow,
    ActorMapping,
    AuditLog,
    BusinessEvent,
    BrowserSession,
    BrowserTab,
    DataSource,
    EngagementStrategy,
    EngagementTask,
    ExecutionQueue,
    ExecutionTask,
    LLMProvider,
    Platform,
    PlatformWeight,
    PlatformSelector,
    Post,
    PostTimeline,
    ProviderRouting,
    PromptTemplate,
    PromptVersion,
    Reply,
    ReplayFile,
    ReplayIndex,
    SchedulerTask,
    StatisticSnapshot,
    SystemSetting,
    TGEProfile,
    WorkerNode,
)


SEED_VERSION = "sprint-04-ai-runtime"


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
            ("Instagram", "instagram", "PLANNED"),
            ("TikTok", "tiktok", "PLANNED"),
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
                        "actor_name": actor_id.split("/")[-1],
                        "remark": "Seed Apify configuration. Replace actor input before real collection.",
                        "input_json": {"queries": ["automation", "workflow"], "maxItems": 10},
                        "max_items": 10,
                    },
                    status="READY",
                )
                db.add(item)
                db.flush()
            sources.append(item)

        reddit_mapping = db.scalar(
            select(ActorMapping).where(
                ActorMapping.actor_id == "demo/reddit-discovery",
                ActorMapping.platform == "reddit",
            )
        )
        if not reddit_mapping:
            db.add(
                ActorMapping(
                    data_source_id=sources[0].id,
                    actor_id="demo/reddit-discovery",
                    platform="reddit",
                    mapping_name="Default Reddit Mapping",
                    title_path="title",
                    content_path="selftext",
                    url_path="url",
                    author_path="author",
                    author_id_path="author_id",
                    community_path="subreddit",
                    source_post_id_path="id",
                    published_at_path="created_utc",
                    score_path="score",
                    comment_count_path="num_comments",
                    media_path="media",
                    language_path="language",
                    enabled=True,
                    remark="Default Reddit actor mapping seed.",
                )
            )

        now = datetime.now(timezone.utc)
        post_specs = [
            ("reddit", 0, "ADHD", "focus_builder", "How do you keep a routine when every day feels different?", "I have tried several planners but stop using them after a week.", ["routine", "question"], "WAITING_REVIEW"),
            ("reddit", 0, "productivity", "workflow_notes", "Looking for a calmer way to manage recurring tasks", "Most tools feel too complicated for my small team.", ["workflow", "purchase_intent"], "SCHEDULED"),
            ("reddit", 0, "SaaS", "founder_weekly", "What did you automate first in your SaaS operations?", "Curious which repetitive process gave you the fastest return.", ["saas", "discussion"], "SCHEDULED"),
            ("reddit", 0, "ADHD", "day_by_day", "A lightweight weekly review that finally worked", "Sharing a small routine that has been sustainable for me.", ["experience", "routine"], "SCHEDULED"),
            ("x", 1, "builders", "ship_small", "What is your smallest useful automation?", "Collecting examples of practical local-first workflows.", ["automation", "question"], "WAITING_REVIEW"),
            ("x", 1, "founders", "quiet_ops", "Operational dashboards should reduce decisions", "A good dashboard makes the next action obvious.", ["dashboard", "operations"], "SCHEDULED"),
            ("x", 1, "ai-tools", "model_router", "Local models for classification tasks", "Small models can be effective when the output schema is constrained.", ["local_llm", "ai"], "SCHEDULED"),
            ("facebook", 1, "Small Business Systems", "ops_owner", "How do small teams track recurring work?", "We need something simple enough to maintain every day.", ["small_business", "workflow"], "WAITING_REVIEW"),
            ("facebook", 1, "Productivity Community", "weekly_reset", "A simple planning ritual for Monday mornings", "This checklist helped our team start the week with less noise.", ["planning", "experience"], "SCHEDULED"),
            ("facebook", 1, "SaaS Operators", "metric_maker", "Which metric belongs on the first dashboard?", "I am deciding between queue health and conversion metrics.", ["metrics", "dashboard"], "SCHEDULED"),
        ]
        for index in range(11, 21):
            platform_slug = ["reddit", "x", "facebook"][index % 3]
            source_index = 0 if platform_slug == "reddit" else 1
            status = "SCHEDULED" if index <= 18 else "WAITING_REVIEW"
            post_specs.append(
                (
                    platform_slug,
                    source_index,
                    "ADHD" if platform_slug == "reddit" else "operators",
                    f"pipeline_author_{index}",
                    f"Pipeline demo post {index}: practical workflow question",
                    "Seed content for validating Data Source to Post Pool to AI Workspace to Scheduler.",
                    ["pipeline", "sprint01"],
                    status,
                )
            )
        posts = []
        for index, spec in enumerate(post_specs, start=1):
            platform_slug, source_index, community, author, title, content, tags, status = spec
            source_post_id = f"seed-{index:03d}"
            item = db.scalar(
                select(Post).where(Post.source_post_id == source_post_id)
            )
            if not item:
                url = f"https://example.com/{platform_slug}/{source_post_id}"
                item = Post(
                    platform_id=platforms[platform_slug].id,
                    data_source_id=sources[source_index].id,
                    source_post_id=source_post_id,
                    url_hash=hashlib.sha256(url.encode("utf-8")).hexdigest(),
                    community=community,
                    author=author,
                    title=title,
                    content=content,
                    url=url,
                    tags=tags,
                    raw_json={"seed": True, "source_post_id": source_post_id},
                    published_at=now - timedelta(hours=index * 2),
                    status=status,
                    pipeline_stage=status,
                )
                db.add(item)
                db.flush()
            else:
                item.status = status
                item.pipeline_stage = status
            posts.append(item)

        ai_tasks = []
        strategies = ["EDUCATION", "PURE_HELP", "EXPERIENCE", "SUPPORTIVE", "DIRECT_REPLY"]
        ai_specs = []
        for index, post in enumerate(posts, start=1):
            if index <= 10:
                task_status = "APPROVED"
            elif index <= 20:
                task_status = "GENERATED"
            else:
                task_status = "REVIEWING"
            ai_specs.append(
                (
                    post,
                    strategies[index % len(strategies)],
                    60 + (index % 35),
                    8 + (index % 18),
                    task_status,
                )
            )
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
                    model="mock-v0.3",
                    strategy=strategy,
                    commercial_score=commercial,
                    risk_score=risk,
                    result={
                        "intent": ["QUESTION", "SUPPORT"],
                        "pain_point": "Needs a practical, low-friction next step.",
                        "recommended_strategy": strategy,
                        "summary": "Seed AI analysis result for local verification.",
                        "confidence": round(0.8 + index * 0.04, 2),
                        "seed": True,
                    },
                    status=task_status,
                )
                db.add(task)
                db.flush()
            else:
                task.strategy = strategy
                task.commercial_score = commercial
                task.risk_score = risk
                task.status = task_status
            analysis = db.scalar(
                select(AIAnalysisResult).where(AIAnalysisResult.ai_task_id == task.id)
            )
            if not analysis:
                db.add(
                    AIAnalysisResult(
                        post_id=post.id,
                        ai_task_id=task.id,
                        intent="QUESTION",
                        pain_point="Needs a practical, low-friction next step.",
                        commercial_score=commercial,
                        risk_score=risk,
                        recommended_strategy=strategy,
                        summary="Seed AI analysis result for local verification.",
                        provider_used="mock-seed",
                        model_used="mock-v0.3",
                        generation_source="MOCK",
                        raw_result=task.result,
                    )
                )
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
            else:
                reply.status = "APPROVED" if task_status == "APPROVED" else "GENERATED"
            ai_tasks.append((task, reply))

        account_specs = [
            ("reddit", "atos_reddit_demo", "ATOS Reddit Demo", 92),
            ("reddit", "atos_reddit_backup", "ATOS Reddit Backup", 89),
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
                    profile_url=f"https://example.com/{platform_slug}/{username}",
                    account_level="seed",
                    karma_score=120 if platform_slug == "reddit" else 0,
                    followers_count=50,
                    following_count=25,
                    account_age_days=180,
                    health_score=health_score,
                    risk_status="LOW",
                    daily_limits={"browse": 20, "reply": 5, "like": 8},
                    working_time={
                        "timezone": "Asia/Shanghai",
                        "windows": [
                            {"day": "MON", "start": "00:00", "end": "23:59"},
                            {"day": "TUE", "start": "00:00", "end": "23:59"},
                            {"day": "WED", "start": "00:00", "end": "23:59"},
                            {"day": "THU", "start": "00:00", "end": "23:59"},
                            {"day": "FRI", "start": "00:00", "end": "23:59"},
                            {"day": "SAT", "start": "00:00", "end": "23:59"},
                            {"day": "SUN", "start": "00:00", "end": "23:59"},
                        ],
                    },
                    remark="Seed account for local scheduler validation.",
                    status="ACTIVE",
                )
                db.add(item)
                db.flush()
            else:
                item.risk_status = item.risk_status or item.risk_level or "LOW"
                item.profile_url = item.profile_url or f"https://example.com/{platform_slug}/{username}"
                item.account_level = item.account_level or "seed"
                item.remark = item.remark or "Seed account for local scheduler validation."
                item.working_time = item.working_time or {"timezone": "Asia/Shanghai", "windows": []}
            limit = db.scalar(select(AccountLimit).where(AccountLimit.account_id == item.id))
            if not limit:
                db.add(
                    AccountLimit(
                        account_id=item.id,
                        browse_daily_limit=20,
                        like_daily_limit=8,
                        bookmark_daily_limit=5,
                        visit_profile_daily_limit=5,
                        reply_daily_limit=5,
                    )
                )
            existing_windows = db.scalars(
                select(AccountWorkingWindow).where(AccountWorkingWindow.account_id == item.id)
            ).all()
            if not existing_windows:
                for day in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]:
                    db.add(
                        AccountWorkingWindow(
                            account_id=item.id,
                            day_of_week=day,
                            start_time="00:00",
                            end_time="23:59",
                            timezone="Asia/Shanghai",
                            enabled=True,
                        )
                    )
            accounts.append(item)

        for index, (account, environment_id) in enumerate(
            zip(accounts, ["tge-demo-001", "tge-demo-002", "tge-demo-003", "tge-demo-004"]),
            start=1,
        ):
            profile = db.scalar(
                select(TGEProfile).where(
                    (TGEProfile.bound_account_id == account.id)
                    | (TGEProfile.account_id == account.id)
                )
            )
            if not profile:
                db.add(
                    TGEProfile(
                        account_id=account.id,
                        bound_account_id=account.id,
                        platform_id=account.platform_id,
                        environment_id=environment_id,
                        tge_environment_id=environment_id,
                        name=f"{account.display_name} Environment",
                        profile_name=f"{account.display_name} Environment",
                        api_base_url="http://127.0.0.1:50326",
                        proxy_region="US",
                        proxy_type="residential",
                        status="ACTIVE",
                        connection_status="SUCCESS",
                        runtime_status="UNKNOWN",
                        remark=f"Seed TGE profile {index}.",
                    )
                )
            else:
                profile.bound_account_id = profile.bound_account_id or account.id
                profile.account_id = profile.account_id or account.id
                profile.platform_id = profile.platform_id or account.platform_id
                profile.tge_environment_id = profile.tge_environment_id or profile.environment_id or environment_id
                profile.environment_id = profile.environment_id or profile.tge_environment_id
                profile.profile_name = profile.profile_name or profile.name or f"{account.display_name} Environment"
                profile.name = profile.name or profile.profile_name
                profile.status = "ACTIVE"
                profile.connection_status = profile.connection_status or "SUCCESS"
                profile.runtime_status = profile.runtime_status or "UNKNOWN"

        scheduler_specs = []
        for index in range(8):
            post = posts[index + 1] if index + 1 < len(posts) else posts[index]
            ai_task, reply = ai_tasks[index + 1] if index + 1 < len(ai_tasks) else ai_tasks[index]
            scheduler_specs.append(("REPLY", accounts[index % len(accounts)], post, ai_task, reply, "HIGH" if index < 2 else "MEDIUM"))
        for index, (task_type, account, post, ai_task, reply, priority) in enumerate(
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
                        ai_task_id=ai_task.id if ai_task else None,
                        reply_id=reply.id if reply else None,
                        source="PIPELINE",
                        priority=priority,
                        scheduled_at=now + timedelta(minutes=index * 15),
                        payload={
                            "mode": "HUMAN_IN_THE_LOOP",
                            "seed": True,
                            "action_type": "PREPARE_REPLY" if task_type == "REPLY" else "MIXED_ENGAGEMENT" if task_type == "ENGAGEMENT" else "OPEN_PAGE",
                            "url": post.url,
                            "post_url": post.url,
                            "reply_content": reply.content if reply else None,
                        },
                        status="QUEUED",
                    )
                )
            else:
                item.ai_task_id = item.ai_task_id or (ai_task.id if ai_task else None)
                item.source = item.source or "PIPELINE"

        selector_specs = [
            ("reddit", "reply_box", 'div[contenteditable="true"]', "css", "Primary Reddit contenteditable reply box"),
            ("reddit", "comment_button", 'button:has-text("Comment")', "css", "Manual submit button reference only; ATOS never clicks it in v0.8"),
            ("reddit", "login_required", 'text="Log In"', "text", "Detect login prompt"),
            ("reddit", "rate_limited", 'text="You are doing that too much"', "text", "Detect rate limit text"),
            ("reddit", "comment_disabled", 'text="comments are locked"', "text", "Detect disabled comments"),
        ]
        for platform, key, value, selector_type, remark in selector_specs:
            selector = db.scalar(
                select(PlatformSelector).where(
                    PlatformSelector.platform == platform,
                    PlatformSelector.selector_key == key,
                    PlatformSelector.selector_value == value,
                )
            )
            if not selector:
                db.add(
                    PlatformSelector(
                        platform=platform,
                        selector_key=key,
                        selector_value=value,
                        selector_type=selector_type,
                        enabled=True,
                        remark=remark,
                    )
                )

        setting_specs = [
            ("ai.default_provider", "AI", {"provider": "mock", "model": "mock-v0.3"}, False),
            (
                "scheduler.defaults",
                "SCHEDULER",
                {
                    "scheduler_enabled": True,
                    "auto_queue_on_approval": False,
                    "default_strategy": "ROUND_ROBIN",
                    "enable_random_delay": False,
                    "min_delay_seconds": 120,
                    "max_delay_seconds": 480,
                    "enable_platform_round_robin": True,
                    "enable_weighted_round_robin": False,
                    "max_tasks_per_account_per_day": 5,
                    "max_tasks_per_platform_per_day": 20,
                    "last_dispatched_platform_id": None,
                },
                False,
            ),
            (
                "execution.tge",
                "EXECUTION",
                {
                    "tge_api_base_url": "http://127.0.0.1:50326",
                    "tge_api_key": "",
                    "default_timeout_seconds": 10,
                    "enable_tge_connection_test": False,
                    "enable_auto_start_environment": False,
                    "enable_auto_attach_environment": False,
                    "enable_auto_close_tab": True,
                    "remark": "Seed TGE adapter config. v0.8 supports semi-auto PREPARE_REPLY only.",
                },
                True,
            ),
            ("data.apify", "DATA_CENTER", {"enabled": False}, True),
            (
                "execution.playwright",
                "EXECUTION",
                {
                    "playwright_enabled": False,
                    "playwright_mock_mode": True,
                    "playwright_timeout_seconds": 30,
                    "playwright_headless": False,
                    "playwright_default_wait_ms": 1000,
                    "enable_screenshot": True,
                    "enable_html_snapshot": True,
                    "enable_auto_close_tab": True,
                    "enable_replay_capture": True,
                },
                False,
            ),
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
            ("imported_posts", "SYSTEM", 20),
            ("ai_tasks", "SYSTEM", 20),
            ("scheduler_queue", "SYSTEM", 8),
            ("pipeline_import", "SYSTEM", 20),
            ("pipeline_ai", "SYSTEM", 20),
            ("pipeline_approve", "SYSTEM", 10),
            ("pipeline_reject", "SYSTEM", 0),
            ("pipeline_schedule", "SYSTEM", 8),
            ("active_accounts", "SYSTEM", 3),
            ("reply_success_rate", "REDDIT", 92),
            ("average_risk_score", "SYSTEM", 15.3),
            ("browse_count", "REDDIT", 12),
            ("like_count", "REDDIT", 4),
            ("visit_profile_count", "REDDIT", 3),
            ("engagement_success_rate", "REDDIT", 100),
            ("warmup_before_reply_count", "REDDIT", 2),
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
            else:
                item.value = value
                item.metadata_json = {"seed": True}

        strategy_specs = [
            {
                "name": "Reddit Silent Browse",
                "platform": "reddit",
                "strategy_type": "SILENT_BROWSE",
                "browse_count_min": 3,
                "browse_count_max": 5,
                "like_count_min": 0,
                "like_count_max": 0,
                "visit_profile_count_min": 0,
                "visit_profile_count_max": 1,
                "before_reply_enabled": False,
                "remark": "Seed independent browse strategy.",
            },
            {
                "name": "Reddit Reply Warm-up",
                "platform": "reddit",
                "strategy_type": "REPLY_WARMUP",
                "browse_count_min": 2,
                "browse_count_max": 4,
                "like_count_min": 1,
                "like_count_max": 2,
                "visit_profile_count_min": 0,
                "visit_profile_count_max": 1,
                "before_reply_enabled": True,
                "remark": "Seed warm-up strategy inserted before reply tasks.",
            },
        ]
        strategies = []
        for spec in strategy_specs:
            strategy = db.scalar(select(EngagementStrategy).where(EngagementStrategy.name == spec["name"]))
            if not strategy:
                strategy = EngagementStrategy(**spec)
                db.add(strategy)
                db.flush()
            strategies.append(strategy)

        for index, strategy in enumerate(strategies, start=1):
            account = accounts[0]
            task = db.scalar(
                select(EngagementTask).where(
                    EngagementTask.strategy_id == strategy.id,
                    EngagementTask.account_id == account.id,
                    EngagementTask.source_value == "seed",
                )
            )
            if not task:
                db.add(
                    EngagementTask(
                        strategy_id=strategy.id,
                        account_id=account.id,
                        platform=strategy.platform,
                        source_type="POST_POOL",
                        source_value="seed",
                        status="QUEUED",
                        browse_target_count=strategy.browse_count_min,
                        like_target_count=strategy.like_count_min,
                        visit_profile_target_count=strategy.visit_profile_count_min,
                        priority="MEDIUM",
                        scheduled_at=now + timedelta(minutes=10 * index),
                    )
                )

        existing_engagement_count = len(db.scalars(select(EngagementTask)).all())
        for index in range(existing_engagement_count + 1, 6):
            strategy = strategies[index % len(strategies)]
            db.add(
                EngagementTask(
                    strategy_id=strategy.id,
                    account_id=accounts[0].id,
                    platform=strategy.platform,
                    source_type="POST_POOL",
                    source_value=f"seed-extra-{index}",
                    status="QUEUED",
                    browse_target_count=2,
                    like_target_count=1,
                    visit_profile_target_count=1 if index % 2 == 0 else 0,
                    priority="LOW",
                    scheduled_at=now + timedelta(minutes=12 * index),
                )
            )

        scheduler_items = db.scalars(select(SchedulerTask).order_by(SchedulerTask.id.asc())).all()
        for scheduler_task in scheduler_items[:5]:
            existing_execution = db.scalar(
                select(ExecutionTask).where(ExecutionTask.scheduler_task_id == scheduler_task.id)
            )
            if existing_execution:
                continue
            profile = db.scalar(
                select(TGEProfile).where(
                    (TGEProfile.bound_account_id == scheduler_task.account_id)
                    | (TGEProfile.account_id == scheduler_task.account_id)
                )
            )
            platform = db.get(Platform, scheduler_task.platform_id)
            execution = ExecutionTask(
                scheduler_task_id=scheduler_task.id,
                account_id=scheduler_task.account_id,
                tge_profile_id=profile.id if profile else None,
                platform=platform.slug if platform else None,
                action_type=(scheduler_task.payload or {}).get("action_type", "OPEN_PAGE"),
                strategy=(scheduler_task.payload or {}).get("strategy"),
                payload_json=scheduler_task.payload or {},
                status="RECEIVED",
                precheck_status="PENDING",
                environment_status=profile.runtime_status if profile else "UNKNOWN",
            )
            db.add(execution)
            db.flush()
            db.add(ReplayFile(execution_task_id=execution.id))
            db.add(ReplayIndex(execution_task_id=execution.id, status="INDEXED", artifact_count=0, manifest_json={"seed": True}))

        worker = db.scalar(select(WorkerNode).where(WorkerNode.name == "local-worker"))
        if not worker:
            worker = WorkerNode(
                name="local-worker",
                status="ONLINE",
                host="localhost",
                version="sprint-02",
                capability={"mode": "local", "browser_automation": False},
                last_heartbeat=now,
            )
            db.add(worker)
            db.flush()
        else:
            worker.status = "ONLINE"
            worker.version = "sprint-02"
            worker.capability = {"mode": "local", "browser_automation": False}
            worker.last_heartbeat = now

        remote_worker = db.scalar(select(WorkerNode).where(WorkerNode.name == "remote-worker-demo"))
        if not remote_worker:
            remote_worker = WorkerNode(
                name="remote-worker-demo",
                status="ONLINE",
                host="remote-demo",
                version="sprint-03",
                capability={"mode": "remote", "browser_automation": False},
                last_heartbeat=now,
            )
            db.add(remote_worker)
            db.flush()
        else:
            remote_worker.status = "ONLINE"
            remote_worker.version = "sprint-03"
            remote_worker.last_heartbeat = now

        demo_statuses = ["RUNNING"] * 10 + ["WAITING_MANUAL"] * 10 + ["SUCCESS"] * 10
        for index, status in enumerate(demo_statuses, start=1):
            task_uuid_marker = f"sprint02-demo-{index:02d}"
            payload = {
                "seed": True,
                "demo_key": task_uuid_marker,
                "action_type": "RUNTIME_PLACEHOLDER",
                "browser_automation": False,
                "message": "Execution Runtime demo task. No browser automation is performed.",
            }
            existing = db.scalar(
                select(ExecutionTask).where(
                    ExecutionTask.payload_json["demo_key"].as_string() == task_uuid_marker
                )
            )
            if not existing:
                account = accounts[index % len(accounts)]
                profile = db.scalar(
                    select(TGEProfile).where(
                        (TGEProfile.bound_account_id == account.id)
                        | (TGEProfile.account_id == account.id)
                    )
                )
                existing = ExecutionTask(
                    scheduler_task_id=None,
                    account_id=account.id,
                    tge_profile_id=profile.id if profile else None,
                    platform=(db.get(Platform, account.platform_id).slug if account.platform_id else None),
                    action_type="RUNTIME_PLACEHOLDER",
                    strategy="EXECUTION_READY",
                    payload_json=payload,
                    status=status,
                    queue_status=status,
                    worker_node_id=worker.id if status in {"RUNNING", "WAITING_MANUAL"} else None,
                    claimed_at=now - timedelta(minutes=index) if status in {"RUNNING", "WAITING_MANUAL", "SUCCESS"} else None,
                    last_heartbeat_at=now if status in {"RUNNING", "WAITING_MANUAL"} else None,
                    started_at=now - timedelta(minutes=index) if status in {"RUNNING", "WAITING_MANUAL", "SUCCESS"} else None,
                    finished_at=now - timedelta(minutes=index - 1) if status == "SUCCESS" else None,
                    precheck_status="SUCCESS",
                    environment_status="UNKNOWN",
                )
                db.add(existing)
                db.flush()
                db.add(ReplayFile(execution_task_id=existing.id))
                db.add(ReplayIndex(execution_task_id=existing.id, status="INDEXED", artifact_count=0, manifest_json=payload))
            else:
                existing.status = status
                existing.queue_status = status
                existing.worker_node_id = worker.id if status in {"RUNNING", "WAITING_MANUAL"} else None
            queue = db.scalar(
                select(ExecutionQueue).where(ExecutionQueue.execution_task_id == existing.id)
            )
            if not queue:
                db.add(
                    ExecutionQueue(
                        scheduler_task_id=existing.scheduler_task_id,
                        execution_task_id=existing.id,
                        worker_node_id=worker.id if status in {"RUNNING", "WAITING_MANUAL"} else None,
                        priority="MEDIUM",
                        status=status,
                        queued_at=now - timedelta(minutes=index + 30),
                        claimed_at=existing.claimed_at,
                        started_at=existing.started_at,
                        finished_at=existing.finished_at,
                    )
                )
            else:
                queue.status = status
                queue.worker_node_id = worker.id if status in {"RUNNING", "WAITING_MANUAL"} else None
                queue.claimed_at = existing.claimed_at
                queue.started_at = existing.started_at
                queue.finished_at = existing.finished_at

        browser_sessions = []
        for index in range(1, 5):
            browser_type = "tge" if index <= 2 else "mock"
            worker_ref = worker if index % 2 else remote_worker
            account = accounts[(index - 1) % len(accounts)]
            profile = db.scalar(
                select(TGEProfile).where(
                    (TGEProfile.bound_account_id == account.id)
                    | (TGEProfile.account_id == account.id)
                )
            )
            session = db.scalar(
                select(BrowserSession).where(
                    BrowserSession.metadata_json["demo_key"].as_string() == f"browser-session-{index}"
                )
            )
            if not session:
                session = BrowserSession(
                    browser_type=browser_type,
                    worker_id=worker_ref.id,
                    account_id=account.id,
                    profile_id=profile.id if profile else None,
                    status="RUNNING",
                    started_at=now - timedelta(minutes=index * 5),
                    last_heartbeat=now - timedelta(seconds=index * 10),
                    metadata_json={"seed": True, "demo_key": f"browser-session-{index}"},
                )
                db.add(session)
                db.flush()
            else:
                session.status = "RUNNING"
                session.worker_id = worker_ref.id
                session.last_heartbeat = now - timedelta(seconds=index * 10)
            browser_sessions.append(session)

        existing_tab_count = db.scalar(
            select(func.count()).select_from(BrowserTab).where(BrowserTab.metadata_json["seed"].as_boolean().is_(True))
        ) or 0
        if existing_tab_count < 15:
            for index in range(1, 16):
                session = browser_sessions[(index - 1) % len(browser_sessions)]
                tab = db.scalar(
                    select(BrowserTab).where(
                        BrowserTab.metadata_json["demo_key"].as_string() == f"browser-tab-{index}"
                    )
                )
                if tab:
                    continue
                db.add(
                    BrowserTab(
                        session_id=session.id,
                        url=f"https://example.com/browser-runtime/tab-{index}",
                        title=f"Browser Runtime Demo Tab {index}",
                        status="OPEN" if index <= 12 else "CLOSED",
                        opened_at=now - timedelta(minutes=index),
                        closed_at=now - timedelta(minutes=index - 1) if index > 12 else None,
                        metadata_json={"seed": True, "demo_key": f"browser-tab-{index}"},
                    )
                )

        platform_weight_specs = {
            "reddit": (50, "Primary discovery platform"),
            "facebook": (30, "Secondary community platform"),
            "x": (20, "Fast signal platform"),
            "instagram": (15, "Future visual platform"),
            "tiktok": (10, "Future video platform"),
        }
        for slug, (weight, remark) in platform_weight_specs.items():
            platform = platforms.get(slug) or db.scalar(select(Platform).where(Platform.slug == slug))
            if not platform:
                continue
            item = db.scalar(
                select(PlatformWeight).where(PlatformWeight.platform_id == platform.id)
            )
            if not item:
                db.add(
                    PlatformWeight(
                        platform_id=platform.id,
                        weight=weight,
                        enabled=True,
                        remark=remark,
                    )
                )

        provider_specs = [
            {
                "provider_name": "Mock Provider",
                "provider_type": "mock",
                "api_base_url": None,
                "api_key": None,
                "model_name": "mock-v0.3",
                "enabled": True,
                "priority": 100,
                "use_for_analysis": True,
                "use_for_reply": True,
                "use_for_embedding": False,
                "is_mock": True,
                "timeout_seconds": 10,
                "max_retries": 0,
                "remark": "Default local provider. No external API call.",
            },
            {
                "provider_name": "OpenAI Provider",
                "provider_type": "openai",
                "api_base_url": "https://api.openai.com/v1",
                "api_key": os.getenv("OPENAI_API_KEY") or None,
                "model_name": os.getenv("DEFAULT_AI_MODEL", "gpt-4.1-mini"),
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
                "priority": 10,
                "use_for_analysis": True,
                "use_for_reply": True,
                "use_for_embedding": False,
                "is_mock": False,
                "timeout_seconds": 30,
                "max_retries": 1,
                "remark": "Optional real provider. Enable after adding an API key.",
            },
            {
                "provider_name": "Ollama Provider",
                "provider_type": "ollama",
                "api_base_url": "http://127.0.0.1:11434",
                "api_key": None,
                "model_name": "llama3.1:8b",
                "enabled": False,
                "priority": 50,
                "use_for_analysis": True,
                "use_for_reply": True,
                "use_for_embedding": True,
                "is_mock": False,
                "timeout_seconds": 60,
                "max_retries": 0,
                "remark": "Local LLM provider scaffold. Enable when Ollama is available.",
            },
        ]
        for spec in provider_specs:
            provider = db.scalar(
                select(LLMProvider).where(
                    LLMProvider.provider_name == spec["provider_name"]
                )
            )
            if not provider:
                provider = LLMProvider(**spec)
                db.add(provider)
                db.flush()
            provider.health_status = provider.health_status or "UNKNOWN"

        prompt_specs = [
            (
                "Default Analysis Prompt",
                "analysis_prompt",
                None,
                None,
                None,
                """Analyze this post and return JSON only:
{
  "intent": "...",
  "pain_point": "...",
  "commercial_score": 0,
  "risk_score": 0,
  "recommended_strategy": "...",
  "summary": "..."
}

Title: {{title}}
Content: {{content}}
Community: {{community}}
Author: {{author}}
URL: {{url}}
""",
            ),
            (
                "Default Reply Prompt",
                "reply_prompt",
                None,
                None,
                "supportive",
                """Write a helpful, non-spammy reply draft.
Strategy: {{strategy}}
Tone: {{tone}}
Variables: {{variables}}

Title: {{title}}
Content: {{content}}
Community: {{community}}
""",
            ),
        ]
        for name, template_type, platform, strategy, tone, content in prompt_specs:
            template = db.scalar(
                select(PromptTemplate).where(PromptTemplate.name == name)
            )
            if not template:
                template = PromptTemplate(
                    name=name,
                    template_type=template_type,
                    platform=platform,
                    strategy=strategy,
                    tone=tone,
                    content=content,
                    version="v1.2",
                    enabled=True,
                )
                db.add(template)
                db.flush()
            prompt_version = db.scalar(
                select(PromptVersion).where(
                    PromptVersion.prompt_template_id == template.id,
                    PromptVersion.version == "v1.2",
                )
            )
            if not prompt_version:
                db.add(
                    PromptVersion(
                        prompt_template_id=template.id,
                        version="v1.2",
                        content=template.content,
                        variables_schema={
                            "title": "post title",
                            "content": "post body",
                            "community": "community/subreddit",
                            "author": "post author",
                            "strategy": "reply strategy",
                            "tone": "reply tone",
                            "variables": "runtime variables JSON",
                        },
                        platform=template.platform,
                        strategy=template.strategy,
                        tone=template.tone,
                        enabled=True,
                        is_default=True,
                    )
                )

        mock_provider = db.scalar(select(LLMProvider).where(LLMProvider.provider_type == "mock"))
        openai_provider = db.scalar(select(LLMProvider).where(LLMProvider.provider_type == "openai"))
        route_specs = [
            ("Default Analysis Route", "ANALYSIS", None),
            ("Default Reply Route", "REPLY", None),
            ("Default Reply Generation Route", "REPLY_GENERATION", None),
            ("Default Embedding Route", "EMBEDDING", None),
        ]
        for name, task_type, strategy in route_specs:
            route = db.scalar(select(ProviderRouting).where(ProviderRouting.name == name))
            if not route:
                db.add(
                    ProviderRouting(
                        name=name,
                        platform=None,
                        task_type=task_type,
                        strategy=strategy,
                        min_commercial_score=0,
                        max_risk_score=100,
                        preferred_provider_id=openai_provider.id if openai_provider and openai_provider.enabled else mock_provider.id if mock_provider else None,
                        fallback_provider_id=mock_provider.id if mock_provider else None,
                        enabled=True,
                        priority=10 if task_type != "EMBEDDING" else 50,
                        remark="Seed provider routing rule. Falls back to Mock Provider when real providers are unavailable.",
                    )
                )

        for post in posts:
            existing_timeline = db.scalar(
                select(PostTimeline).where(PostTimeline.post_id == post.id)
            )
            if not existing_timeline:
                status_flow = ["NEW", "NORMALIZED", "READY_FOR_AI", "ANALYZING", "AI_COMPLETED", "WAITING_REVIEW"]
                if post.status in {"APPROVED", "SCHEDULED"}:
                    status_flow.append("APPROVED")
                if post.status == "SCHEDULED":
                    status_flow.append("SCHEDULED")
                old_status = None
                for step_index, step in enumerate(status_flow, start=1):
                    db.add(
                        PostTimeline(
                            post_id=post.id,
                            event_name={
                                "NORMALIZED": "PostNormalized",
                                "READY_FOR_AI": "PostReadyForAI",
                                "AI_COMPLETED": "AICompleted",
                                "APPROVED": "ReplyApproved",
                                "SCHEDULED": "TaskScheduled",
                            }.get(step, "PostStatusChanged"),
                            old_status=old_status,
                            new_status=step,
                            actor="seed",
                            detail={"seed": True, "step": step_index},
                            created_at=now - timedelta(minutes=60 - step_index),
                        )
                    )
                    old_status = step
            if not db.scalar(
                select(BusinessEvent).where(
                    BusinessEvent.post_id == post.id,
                    BusinessEvent.event_name == "PostImported",
                )
            ):
                db.add(
                    BusinessEvent(
                        event_name="PostImported",
                        entity_type="Post",
                        entity_id=post.id,
                        post_id=post.id,
                        payload={"seed": True, "status": post.status},
                    )
                )
            if post.status in {"APPROVED", "SCHEDULED"} and not db.scalar(
                select(AuditLog).where(AuditLog.entity_uuid == post.uuid, AuditLog.action == "Approve")
            ):
                db.add(
                    AuditLog(
                        trace_id="seed",
                        action="Approve",
                        entity_type="Post",
                        entity_uuid=post.uuid,
                        actor="seed",
                        detail={"post_id": post.id},
                    )
                )
            if post.status == "SCHEDULED" and not db.scalar(
                select(AuditLog).where(AuditLog.entity_uuid == post.uuid, AuditLog.action == "Schedule")
            ):
                db.add(
                    AuditLog(
                        trace_id="seed",
                        action="Schedule",
                        entity_type="Post",
                        entity_uuid=post.uuid,
                        actor="seed",
                        detail={"post_id": post.id},
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
            "ATOS acceptance seed ready: 5 platforms, 2 data sources, "
            "20 posts, 20 AI tasks, 8 scheduler tasks, 4 accounts, "
            "4 TGE profiles, pipeline statistics, 3 LLM providers, 2 prompt templates, "
            "2 prompt versions, 4 provider routes, 5 platform weights, 2 engagement strategies, "
            "30 execution runtime demo tasks, 2 workers, 4 browser sessions, 15 browser tabs, "
            "5 engagement tasks, 1 actor mapping."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
