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
    AccountPerformance,
    AccountWorkingWindow,
    ActorMapping,
    AuditLog,
    BusinessEvent,
    BrowserSession,
    BrowserTab,
    ContentPerformance,
    DataSource,
    EngagementStrategy,
    EngagementTask,
    ExecutionQueue,
    ExecutionTask,
    Experiment,
    IntelligenceRecommendation,
    LLMProvider,
    Platform,
    PlatformPerformance,
    PlatformRegistry,
    PlatformWeight,
    PlatformSelector,
    Post,
    PostTimeline,
    ProviderRouting,
    PromptTemplate,
    PromptVersion,
    Reply,
    ReplyScore,
    ReplySimilarity,
    ReplyTask,
    ReplayFile,
    ReplayIndex,
    SchedulerTask,
    SubmissionLog,
    SubmissionTask,
    StrategyPerformance,
    StatisticSnapshot,
    RuntimeMetric,
    SystemAlert,
    SystemSetting,
    TaskLock,
    TGEProfile,
    TimePerformance,
    WorkerLog,
    WorkerNode,
)


SEED_VERSION = "sprint-11-x-adapter-v1"


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
            ("X", "x", "ACTIVE"),
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

        platform_registry_specs = [
            ("reddit", "RedditAdapter", "v1", ["REPLY", "BROWSE", "LIKE", "PROFILE_VISIT"], "HEALTHY"),
            (
                "x",
                "XAdapter",
                "v1",
                ["BROWSE", "OPEN_POST", "REPLY", "REPLY_FILL", "MANUAL_CONFIRM", "SUBMISSION_SCAFFOLD", "LIKE", "PROFILE_VISIT"],
                "HEALTHY",
            ),
            ("facebook", "FacebookAdapter", "v1-scaffold", ["BROWSE", "LIKE", "PROFILE_VISIT"], "HEALTHY"),
            ("instagram", "InstagramAdapter", "v1-scaffold", ["BROWSE", "LIKE", "PROFILE_VISIT"], "HEALTHY"),
            ("tiktok", "TikTokAdapter", "v1-scaffold", ["BROWSE", "LIKE", "PROFILE_VISIT"], "HEALTHY"),
        ]
        for platform_name, adapter_name, version, capabilities, status in platform_registry_specs:
            registry = db.scalar(
                select(PlatformRegistry).where(PlatformRegistry.platform_name == platform_name)
            )
            if not registry:
                db.add(
                    PlatformRegistry(
                        platform_name=platform_name,
                        adapter_name=adapter_name,
                        enabled=True,
                        version=version,
                        capabilities={capability: True for capability in capabilities},
                        status=status,
                    )
                )
            else:
                registry.adapter_name = adapter_name
                registry.enabled = True
                registry.version = version
                registry.capabilities = {capability: True for capability in capabilities}
                registry.status = status

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

        x_mapping = db.scalar(
            select(ActorMapping).where(
                ActorMapping.actor_id == "demo/social-search",
                ActorMapping.platform == "x",
            )
        )
        if not x_mapping:
            db.add(
                ActorMapping(
                    data_source_id=sources[1].id,
                    actor_id="demo/social-search",
                    platform="x",
                    mapping_name="Default X Mapping",
                    title_path="text",
                    content_path="text",
                    url_path="url",
                    author_path="author_handle",
                    author_id_path="author_id",
                    community_path="community",
                    source_post_id_path="tweet_id",
                    published_at_path="created_at",
                    score_path="engagement_count",
                    comment_count_path="reply_count",
                    media_path="media",
                    language_path="language",
                    enabled=True,
                    remark="Default X actor mapping seed.",
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
        for index in range(21, 28):
            post_specs.append(
                (
                    "x",
                    1,
                    "builders",
                    f"x_builder_{index}",
                    f"X demo post {index}: practical operator workflow",
                    "Seed X content for validating semi-auto reply fill and manual confirmation.",
                    ["x_adapter", "semi_auto"],
                    "WAITING_REVIEW" if index % 2 else "SCHEDULED",
                )
            )
        posts = []
        for index, spec in enumerate(post_specs, start=1):
            platform_slug, source_index, community, author, title, content, tags, status = spec
            source_post_id = f"110000000000000{index:03d}" if platform_slug == "x" else f"seed-{index:03d}"
            item = db.scalar(
                select(Post).where(Post.source_post_id == source_post_id)
            )
            url = (
                f"https://x.com/{author}/status/{source_post_id}"
                if platform_slug == "x"
                else f"https://example.com/{platform_slug}/{source_post_id}"
            )
            raw_json = {
                "seed": True,
                "source_post_id": source_post_id,
                "platform": platform_slug,
            }
            if platform_slug == "x":
                raw_json.update(
                    {
                        "external_post_id": source_post_id,
                        "author_handle": author,
                        "post_url": url,
                        "engagement_count": 10 + index,
                        "reply_count": index % 5,
                        "like_count": 5 + index,
                        "repost_count": index % 3,
                    }
                )
            if not item:
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
                    raw_json=raw_json,
                    published_at=now - timedelta(hours=index * 2),
                    status=status,
                    pipeline_stage=status,
                )
                db.add(item)
                db.flush()
            else:
                item.status = status
                item.pipeline_stage = status
                item.url = url
                item.url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
                item.raw_json = raw_json
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
            scheduler_specs.append(("REPLY_TASK", accounts[index % len(accounts)], post, ai_task, reply, "HIGH" if index < 2 else "MEDIUM"))
        for index, (task_type, account, post, ai_task, reply, priority) in enumerate(
            scheduler_specs, start=1
        ):
            reply_task = db.scalar(select(ReplyTask).where(ReplyTask.reply_id == reply.id))
            if not reply_task:
                reply_task = ReplyTask(
                    post_id=post.id,
                    reply_id=reply.id,
                    platform=platforms["reddit"].slug if post.platform_id == platforms["reddit"].id else db.get(Platform, post.platform_id).slug,
                    account_id=account.id,
                    reply_content=reply.content,
                    execution_mode="SEMI_AUTO",
                    status=["SCHEDULED", "EXECUTING", "WAITING_MANUAL", "CONFIRMED", "FAILED", "APPROVED", "SCHEDULED", "SCHEDULED"][index - 1],
                )
                db.add(reply_task)
                db.flush()
            else:
                reply_task.account_id = reply_task.account_id or account.id
                reply_task.reply_content = reply.content
                reply_task.execution_mode = reply_task.execution_mode or "SEMI_AUTO"
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
                        reply_task_id=reply_task.id if reply_task else None,
                        source="PIPELINE",
                        priority=priority,
                        scheduled_at=now + timedelta(minutes=index * 15),
                        payload={
                            "task_type": "PREPARE_REPLY",
                            "mode": "SEMI_AUTO",
                            "seed": True,
                            "action_type": "PREPARE_REPLY" if task_type == "REPLY_TASK" else "MIXED_ENGAGEMENT" if task_type == "ENGAGEMENT" else "OPEN_PAGE",
                            "reply_task_id": reply_task.id if reply_task else None,
                            "url": post.url,
                            "post_url": post.url,
                            "reply_content": reply.content if reply else None,
                            "execution_mode": "SEMI_AUTO",
                            "metadata": {"reply_id": reply.id if reply else None, "reply_task_id": reply_task.id if reply_task else None},
                        },
                        status="QUEUED",
                    )
                )
            else:
                item.ai_task_id = item.ai_task_id or (ai_task.id if ai_task else None)
                item.reply_task_id = item.reply_task_id or (reply_task.id if reply_task else None)
                item.source = item.source or "PIPELINE"
            item = db.scalar(
                select(SchedulerTask).where(
                    SchedulerTask.task_type == task_type,
                    SchedulerTask.account_id == account.id,
                    SchedulerTask.post_id == post.id,
                )
            )
            if item and reply_task:
                reply_task.scheduler_task_id = item.id

        selector_specs = [
            ("reddit", "PREPARE_REPLY", "reply_box", 'div[contenteditable="true"]', "css", "v1", "Primary Reddit contenteditable reply box"),
            ("reddit", "PREPARE_REPLY", "comment_button", 'button:has-text("Comment")', "css", "v1", "Manual submit button reference only; ATOS never clicks it in v0.8"),
            ("reddit", "PREPARE_REPLY", "login_required", 'text="Log In"', "text", "v1", "Detect login prompt"),
            ("reddit", "PREPARE_REPLY", "rate_limited", 'text="You are doing that too much"', "text", "v1", "Detect rate limit text"),
            ("reddit", "PREPARE_REPLY", "comment_disabled", 'text="comments are locked"', "text", "v1", "Detect disabled comments"),
            ("reddit", "LIKE_POST", "like_button", 'button[aria-label*="upvote" i]', "css", "v1", "Reddit upvote selector scaffold"),
            ("reddit", "VISIT_PROFILE", "profile_link", 'a[href*="/user/"]', "css", "v1", "Reddit author profile link scaffold"),
            ("x", "PREPARE_REPLY", "reply_button", '[data-testid="reply"]', "css", "v1", "X reply button"),
            ("x", "PREPARE_REPLY", "reply_box", '[data-testid="tweetTextarea_0"]', "css", "v1", "X reply editor fallback"),
            ("x", "PREPARE_REPLY", "reply_textarea_or_editor", '[data-testid="tweetTextarea_0"] div[contenteditable="true"], div[role="textbox"][contenteditable="true"]', "css", "v1", "X rich text editor"),
            ("x", "SUBMIT_REPLY", "submit_button_scaffold", '[data-testid="tweetButton"]', "css", "v1", "X submit button scaffold only; auto submit disabled by default"),
            ("x", "PREPARE_REPLY", "login_required_indicator", 'text="Log in"', "text", "v1", "X login required indicator"),
            ("x", "PREPARE_REPLY", "rate_limit_indicator", 'text="Rate limit exceeded"', "text", "v1", "X rate limit indicator"),
            ("x", "PREPARE_REPLY", "error_indicator", '[data-testid="error-detail"]', "css", "v1", "X generic error indicator"),
        ]
        for platform, action_type, key, value, selector_type, version, remark in selector_specs:
            selector = db.scalar(
                select(PlatformSelector).where(
                    PlatformSelector.platform == platform,
                    PlatformSelector.action_type == action_type,
                    PlatformSelector.selector_key == key,
                    PlatformSelector.selector_value == value,
                )
            )
            if not selector:
                db.add(
                    PlatformSelector(
                        platform=platform,
                        action_type=action_type,
                        selector_key=key,
                        selector_value=value,
                        selector_type=selector_type,
                        version=version,
                        enabled=True,
                        remark=remark,
                    )
                )
            else:
                selector.action_type = action_type
                selector.version = version
                selector.enabled = True

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
            (
                "execution.submission",
                "EXECUTION",
                {
                    "default_execution_mode": "SEMI_AUTO",
                    "auto_assisted_enabled": False,
                    "full_auto_enabled": False,
                    "max_retry": 1,
                    "verify_timeout_seconds": 20,
                    "capture_screenshot_enabled": True,
                    "capture_html_enabled": True,
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
            ("platform_tasks", "reddit", 14),
            ("platform_tasks", "x", 5),
            ("platform_tasks", "facebook", 4),
            ("platform_tasks", "instagram", 2),
            ("platform_tasks", "tiktok", 1),
            ("platform_success_rate", "reddit", 92),
            ("platform_failure_rate", "reddit", 8),
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
                reply_task_id=scheduler_task.reply_task_id,
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
            if scheduler_task.reply_task_id:
                reply_task = db.get(ReplyTask, scheduler_task.reply_task_id)
                if reply_task:
                    reply_task.execution_task_id = execution.id
            db.add(ReplayFile(execution_task_id=execution.id))
            db.add(ReplayIndex(execution_task_id=execution.id, status="INDEXED", artifact_count=0, manifest_json={"seed": True}))

        x_account = db.scalar(select(Account).where(Account.username == "atos_x_demo"))
        x_posts = [
            post
            for post in posts
            if post.platform_id == platforms["x"].id
        ][:3]
        x_statuses = ["WAITING_MANUAL", "WAITING_MANUAL", "CONFIRMED"]
        for index, post in enumerate(x_posts, start=1):
            ai_reply = next((item for item in ai_tasks if item[0].post_id == post.id), None)
            if not x_account or not ai_reply:
                continue
            ai_task, reply = ai_reply
            reply.status = "APPROVED"
            reply_task = db.scalar(select(ReplyTask).where(ReplyTask.reply_id == reply.id))
            if not reply_task:
                reply_task = ReplyTask(
                    post_id=post.id,
                    reply_id=reply.id,
                    platform="x",
                    account_id=x_account.id,
                    reply_content=reply.content,
                    execution_mode="SEMI_AUTO",
                    status=x_statuses[index - 1],
                )
                db.add(reply_task)
                db.flush()
            else:
                reply_task.platform = "x"
                reply_task.account_id = x_account.id
                reply_task.reply_content = reply.content
                reply_task.execution_mode = "SEMI_AUTO"
                reply_task.status = x_statuses[index - 1]
            scheduler_task = db.scalar(
                select(SchedulerTask).where(
                    SchedulerTask.reply_task_id == reply_task.id,
                    SchedulerTask.source == "X_ADAPTER_SEED",
                )
            )
            if not scheduler_task:
                scheduler_task = SchedulerTask(
                    task_type="REPLY_TASK",
                    platform_id=platforms["x"].id,
                    account_id=x_account.id,
                    post_id=post.id,
                    ai_task_id=ai_task.id,
                    reply_id=reply.id,
                    reply_task_id=reply_task.id,
                    source="X_ADAPTER_SEED",
                    priority="HIGH",
                    scheduled_at=now + timedelta(minutes=90 + index * 10),
                    payload={
                        "task_type": "PREPARE_REPLY",
                        "action_type": "PREPARE_REPLY",
                        "platform": "x",
                        "url": post.url,
                        "post_url": post.url,
                        "reply_content": reply.content,
                        "execution_mode": "SEMI_AUTO",
                        "capability_required": "REPLY",
                        "metadata": {"reply_id": reply.id, "reply_task_id": reply_task.id, "x_seed": True},
                    },
                    status="DISPATCHED" if index <= 2 else "EXECUTED",
                )
                db.add(scheduler_task)
                db.flush()
            reply_task.scheduler_task_id = scheduler_task.id
            profile = db.scalar(
                select(TGEProfile).where(
                    (TGEProfile.bound_account_id == x_account.id)
                    | (TGEProfile.account_id == x_account.id)
                )
            )
            execution = db.scalar(select(ExecutionTask).where(ExecutionTask.scheduler_task_id == scheduler_task.id))
            if not execution:
                execution = ExecutionTask(
                    scheduler_task_id=scheduler_task.id,
                    reply_task_id=reply_task.id,
                    account_id=x_account.id,
                    tge_profile_id=profile.id if profile else None,
                    platform="x",
                    action_type="PREPARE_REPLY",
                    strategy=ai_task.strategy,
                    payload_json={
                        **(scheduler_task.payload or {}),
                        "browser_type": "mock",
                        "fill_status": "REPLY_FILLED" if index <= 2 else "CONFIRMED",
                        "x_seed": True,
                    },
                    status="WAITING_MANUAL" if index <= 2 else "SUCCESS",
                    queue_status="WAITING_MANUAL" if index <= 2 else "SUCCESS",
                    precheck_status="SUCCESS",
                    environment_status="MOCK",
                )
                db.add(execution)
                db.flush()
                db.add(ReplayFile(execution_task_id=execution.id, after_fill_screenshot_path=f"storage/replay/{execution.uuid}/after_fill.png"))
                db.add(ReplayIndex(execution_task_id=execution.id, status="INDEXED", artifact_count=1, manifest_json={"seed": True, "platform": "x"}))
            reply_task.execution_task_id = execution.id

        worker = db.scalar(select(WorkerNode).where(WorkerNode.name == "local-worker"))
        if not worker:
            worker = WorkerNode(
                name="local-worker",
                status="ONLINE",
                host="localhost",
                hostname="localhost",
                os="macOS",
                ip="127.0.0.1",
                version="sprint-02",
                capability={"mode": "local", "browser_automation": False},
                capabilities={"BROWSER": True, "LOCAL": True},
                worker_type="LOCAL",
                max_concurrent_tasks=2,
                current_tasks=0,
                priority=100,
                region="local",
                health_score=96,
                runtime_status="READY",
                last_seen=now,
                last_heartbeat=now,
            )
            db.add(worker)
            db.flush()
        else:
            worker.status = "ONLINE"
            worker.version = "sprint-08"
            worker.capability = {"mode": "local", "browser_automation": False}
            worker.capabilities = {"BROWSER": True, "LOCAL": True}
            worker.worker_type = "LOCAL"
            worker.max_concurrent_tasks = 2
            worker.priority = 100
            worker.region = "local"
            worker.health_score = 96
            worker.runtime_status = "READY"
            worker.last_seen = now
            worker.last_heartbeat = now

        remote_worker = db.scalar(select(WorkerNode).where(WorkerNode.name == "remote-worker-demo"))
        if not remote_worker:
            remote_worker = WorkerNode(
                name="remote-worker-demo",
                status="ONLINE",
                host="remote-demo",
                hostname="remote-demo",
                os="Linux",
                ip="10.0.0.20",
                version="sprint-03",
                capability={"mode": "remote", "browser_automation": False},
                capabilities={"BROWSER": True, "TGE": False, "PLAYWRIGHT": False},
                worker_type="REMOTE",
                max_concurrent_tasks=3,
                current_tasks=0,
                priority=80,
                region="linux-vps",
                health_score=92,
                cpu=18.5,
                memory=42.0,
                gpu=0.0,
                runtime_status="READY",
                token_version="v1",
                last_seen=now,
                last_heartbeat=now,
            )
            db.add(remote_worker)
            db.flush()
        else:
            remote_worker.status = "ONLINE"
            remote_worker.version = "sprint-08"
            remote_worker.worker_type = "REMOTE"
            remote_worker.capabilities = {"BROWSER": True, "TGE": False, "PLAYWRIGHT": False}
            remote_worker.max_concurrent_tasks = 3
            remote_worker.priority = 80
            remote_worker.region = "linux-vps"
            remote_worker.health_score = 92
            remote_worker.cpu = 18.5
            remote_worker.memory = 42.0
            remote_worker.gpu = 0.0
            remote_worker.runtime_status = "READY"
            remote_worker.last_seen = now
            remote_worker.last_heartbeat = now

        windows_worker = db.scalar(select(WorkerNode).where(WorkerNode.name == "windows-ai-workstation"))
        if not windows_worker:
            windows_worker = WorkerNode(
                name="windows-ai-workstation",
                status="ONLINE",
                host="windows-ai-workstation",
                hostname="WIN-AI-01",
                os="Windows",
                ip="10.0.0.50",
                version="sprint-06",
                capability={"mode": "remote", "browser_automation": True},
                capabilities={"AI": True, "BROWSER": True, "TGE": True, "PLAYWRIGHT": True, "EMBEDDING": True},
                worker_type="REMOTE",
                max_concurrent_tasks=5,
                current_tasks=0,
                priority=10,
                region="windows-ai",
                health_score=98,
                cpu=22.0,
                memory=58.0,
                gpu=12.0,
                runtime_status="READY",
                token_version="v1",
                last_seen=now,
                last_heartbeat=now,
            )
            db.add(windows_worker)
            db.flush()
        else:
            windows_worker.status = "ONLINE"
            windows_worker.version = "sprint-08"
            windows_worker.worker_type = "REMOTE"
            windows_worker.capabilities = {"AI": True, "BROWSER": True, "TGE": True, "PLAYWRIGHT": True, "EMBEDDING": True}
            windows_worker.max_concurrent_tasks = 5
            windows_worker.priority = 10
            windows_worker.region = "windows-ai"
            windows_worker.health_score = 98
            windows_worker.cpu = 22.0
            windows_worker.memory = 58.0
            windows_worker.gpu = 12.0
            windows_worker.runtime_status = "READY"
            windows_worker.last_seen = now
            windows_worker.last_heartbeat = now

        for seed_worker in [worker, remote_worker, windows_worker]:
            if not db.scalar(select(WorkerLog).where(WorkerLog.worker_node_id == seed_worker.id)):
                db.add(
                    WorkerLog(
                        worker_node_id=seed_worker.id,
                        worker_id=seed_worker.name,
                        log_type="application",
                        module="seed",
                        level="INFO",
                        message="Seed worker online",
                        metadata_json={"seed": True, "runtime_status": seed_worker.runtime_status},
                    )
                )

        demo_statuses = ["QUEUED"] * 5 + ["RUNNING"] * 10 + ["WAITING_MANUAL"] * 10 + ["SUCCESS"] * 10
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
                    claimed_by_worker=worker.name if status in {"RUNNING", "WAITING_MANUAL"} else None,
                    claimed_at=now - timedelta(minutes=index) if status in {"RUNNING", "WAITING_MANUAL", "SUCCESS"} else None,
                    last_heartbeat_at=now if status in {"RUNNING", "WAITING_MANUAL"} else None,
                    max_retry=3,
                    retry_delay_seconds=60,
                    retry_strategy="EXPONENTIAL",
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
                existing.claimed_by_worker = worker.name if status in {"RUNNING", "WAITING_MANUAL"} else None
                existing.max_retry = existing.max_retry or 3
                existing.retry_delay_seconds = existing.retry_delay_seconds or 60
                existing.retry_strategy = existing.retry_strategy or "EXPONENTIAL"
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
                        required_capability="BROWSER",
                        queued_at=now - timedelta(minutes=index + 30),
                        claimed_at=existing.claimed_at,
                        started_at=existing.started_at,
                        finished_at=existing.finished_at,
                    )
                )
            else:
                queue.status = status
                queue.worker_node_id = worker.id if status in {"RUNNING", "WAITING_MANUAL"} else None
                queue.required_capability = queue.required_capability or "BROWSER"
                queue.claimed_at = existing.claimed_at
                queue.started_at = existing.started_at
                queue.finished_at = existing.finished_at

        for seed_worker in [worker, remote_worker, windows_worker]:
            seed_worker.current_tasks = db.scalar(
                select(func.count()).select_from(ExecutionTask).where(
                    ExecutionTask.worker_node_id == seed_worker.id,
                    ExecutionTask.status.in_(["CLAIMED", "RUNNING", "WAITING_MANUAL"]),
                )
            ) or 0

        running_task = db.scalar(
            select(ExecutionTask).where(ExecutionTask.status == "RUNNING")
        )
        if running_task and running_task.lock_uuid is None:
            lock = TaskLock(
                resource_type="execution_task",
                resource_id=running_task.id,
                owner_worker_id=running_task.worker_node_id,
                status="ACTIVE",
                expires_at=now + timedelta(minutes=5),
            )
            db.add(lock)
            db.flush()
            running_task.lock_uuid = lock.uuid
            queue = db.scalar(select(ExecutionQueue).where(ExecutionQueue.execution_task_id == running_task.id))
            if queue:
                queue.lock_uuid = lock.uuid
                queue.lock_expires_at = lock.expires_at

        metric_specs = [
            ("automation_task_queue", "SYSTEM", 5),
            ("automation_online_workers", "SYSTEM", 3),
            ("automation_running_tasks", "SYSTEM", 10),
            ("automation_retry_pending", "SYSTEM", 0),
            ("automation_failure_rate", "SYSTEM", 8),
        ]
        for metric, dimension, value in metric_specs:
            existing_metric = db.scalar(
                select(RuntimeMetric).where(
                    RuntimeMetric.metric == metric,
                    RuntimeMetric.dimension == dimension,
                    RuntimeMetric.metadata_json["seed"].as_boolean().is_(True),
                )
            )
            if not existing_metric:
                db.add(RuntimeMetric(metric=metric, dimension=dimension, value=value, metadata_json={"seed": True}))

        alert = db.scalar(
            select(SystemAlert).where(
                SystemAlert.alert_type == "QUEUE_MONITOR_READY",
                SystemAlert.metadata_json["seed"].as_boolean().is_(True),
            )
        )
        if not alert:
            db.add(
                SystemAlert(
                    alert_type="QUEUE_MONITOR_READY",
                    severity="INFO",
                    status="OPEN",
                    message="Automation Runtime monitoring is seeded and ready.",
                    source="automation",
                    metadata_json={"seed": True},
                )
            )

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

        seeded_tabs = db.scalars(
            select(BrowserTab)
            .where(BrowserTab.metadata_json["seed"].as_boolean().is_(True))
            .order_by(BrowserTab.id.asc())
        ).all()
        seeded_executions = db.scalars(
            select(ExecutionTask)
            .where(ExecutionTask.reply_task_id.is_not(None))
            .order_by(ExecutionTask.id.asc())
            .limit(6)
        ).all()
        submission_statuses = ["WAITING_MANUAL", "VERIFIED", "FAILED", "READY", "WAITING_POLICY", "SUBMITTING"]
        for index, execution in enumerate(seeded_executions, start=1):
            reply_task = db.get(ReplyTask, execution.reply_task_id) if execution.reply_task_id else None
            if not reply_task:
                continue
            existing_submission = db.scalar(
                select(SubmissionTask).where(SubmissionTask.reply_task_id == reply_task.id)
            )
            tab = seeded_tabs[(index - 1) % len(seeded_tabs)] if seeded_tabs else None
            status = submission_statuses[index - 1]
            if not existing_submission:
                existing_submission = SubmissionTask(
                    reply_task_id=reply_task.id,
                    execution_task_id=execution.id,
                    platform=reply_task.platform or execution.platform,
                    account_id=reply_task.account_id or execution.account_id,
                    worker_id=execution.worker_node_id or worker.id,
                    browser_session_id=tab.session_id if tab else None,
                    browser_tab_id=tab.id if tab else None,
                    execution_mode=reply_task.execution_mode or "SEMI_AUTO",
                    status=status,
                    submitted_at=now - timedelta(minutes=4) if status in {"VERIFIED", "FAILED"} else None,
                    verified_at=now - timedelta(minutes=2) if status == "VERIFIED" else None,
                    result_url="https://www.reddit.com/comments/mock/submission" if status == "VERIFIED" else None,
                    result_external_id="reddit-mock-comment" if status == "VERIFIED" else None,
                    failure_reason="VERIFICATION_FAILED" if status == "FAILED" else None,
                    retry_count=0,
                    max_retry=1,
                    manual_confirmed=status == "VERIFIED",
                    metadata_json={"seed": True, "demo_key": f"submission-task-{index}"},
                )
                db.add(existing_submission)
                db.flush()
            else:
                existing_submission.status = status
                existing_submission.execution_task_id = execution.id
                existing_submission.browser_session_id = existing_submission.browser_session_id or (tab.session_id if tab else None)
                existing_submission.browser_tab_id = existing_submission.browser_tab_id or (tab.id if tab else None)
                existing_submission.metadata_json = {"seed": True, "demo_key": f"submission-task-{index}"}
            existing_log = db.scalar(
                select(SubmissionLog).where(
                    SubmissionLog.submission_task_id == existing_submission.id,
                    SubmissionLog.step == "SEED_TIMELINE",
                )
            )
            if not existing_log:
                db.add(
                    SubmissionLog(
                        submission_task_id=existing_submission.id,
                        step="SEED_TIMELINE",
                        level="INFO" if status != "FAILED" else "ERROR",
                        message=f"Seed submission task status: {status}",
                        metadata_json={"seed": True, "status": status},
                        screenshot_path=f"storage/replay/{execution.uuid}/after_fill.png",
                    )
                )
            execution.payload_json = {
                **(execution.payload_json or {}),
                "submission_task_id": existing_submission.id,
                "submission_status": status,
                "browser_tab_id": existing_submission.browser_tab_id,
                "browser_session_id": existing_submission.browser_session_id,
            }

        x_seed_executions = db.scalars(
            select(ExecutionTask)
            .where(ExecutionTask.payload_json["x_seed"].as_boolean().is_(True))
            .order_by(ExecutionTask.id.asc())
        ).all()
        for index, execution in enumerate(x_seed_executions, start=1):
            reply_task = db.get(ReplyTask, execution.reply_task_id) if execution.reply_task_id else None
            if not reply_task:
                continue
            tab = seeded_tabs[(index - 1) % len(seeded_tabs)] if seeded_tabs else None
            status = "WAITING_MANUAL" if index <= 2 else "VERIFIED"
            submission = db.scalar(select(SubmissionTask).where(SubmissionTask.reply_task_id == reply_task.id))
            if not submission:
                submission = SubmissionTask(
                    reply_task_id=reply_task.id,
                    execution_task_id=execution.id,
                    platform="x",
                    account_id=execution.account_id,
                    worker_id=execution.worker_node_id or worker.id,
                    browser_session_id=tab.session_id if tab else None,
                    browser_tab_id=tab.id if tab else None,
                    execution_mode="SEMI_AUTO",
                    status=status,
                    submitted_at=now - timedelta(minutes=3) if status == "VERIFIED" else None,
                    verified_at=now - timedelta(minutes=1) if status == "VERIFIED" else None,
                    result_url="https://x.com/mock/status/1" if status == "VERIFIED" else None,
                    result_external_id="x-mock-reply" if status == "VERIFIED" else None,
                    manual_confirmed=status == "VERIFIED",
                    metadata_json={"seed": True, "x_seed": True, "demo_key": f"x-submission-task-{index}"},
                )
                db.add(submission)
                db.flush()
            else:
                submission.platform = "x"
                submission.execution_task_id = execution.id
                submission.status = status
                submission.manual_confirmed = status == "VERIFIED"
                submission.metadata_json = {"seed": True, "x_seed": True, "demo_key": f"x-submission-task-{index}"}
            log = db.scalar(
                select(SubmissionLog).where(
                    SubmissionLog.submission_task_id == submission.id,
                    SubmissionLog.step == "X_SEED_TIMELINE",
                )
            )
            if not log:
                db.add(
                    SubmissionLog(
                        submission_task_id=submission.id,
                        step="X_SEED_TIMELINE",
                        level="INFO",
                        message=f"X seed submission status: {status}",
                        metadata_json={"seed": True, "platform": "x", "status": status},
                        screenshot_path=f"storage/replay/{execution.uuid}/after_fill.png",
                    )
                )
            execution.payload_json = {
                **(execution.payload_json or {}),
                "submission_task_id": submission.id,
                "submission_status": status,
                "browser_tab_id": submission.browser_tab_id,
                "browser_session_id": submission.browser_session_id,
            }

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

        for index, reply in enumerate(db.scalars(select(Reply).order_by(Reply.id.asc())).all(), start=1):
            post = db.get(Post, reply.post_id)
            platform_slug = platforms.get("reddit").slug if platforms.get("reddit") else "reddit"
            if post:
                post_platform = db.get(Platform, post.platform_id)
                platform_slug = post_platform.slug if post_platform else platform_slug
            score_value = max(45, min(96, 62 + (index % 7) * 4))
            reply_score = db.scalar(select(ReplyScore).where(ReplyScore.reply_id == reply.id))
            if not reply_score:
                reply_score = ReplyScore(reply_id=reply.id, post_id=reply.post_id)
                db.add(reply_score)
            reply_score.relevance = min(100, score_value + 3)
            reply_score.quality = min(100, score_value + 5)
            reply_score.engagement = score_value
            reply_score.conversion = 70 if reply.status == "APPROVED" else 40
            reply_score.risk = 8 + (index % 4) * 3
            reply_score.score = score_value
            reply_score.reason = "Seed intelligence score."

            content_perf = db.scalar(select(ContentPerformance).where(ContentPerformance.reply_id == reply.id))
            if not content_perf:
                content_perf = ContentPerformance(post_id=reply.post_id, reply_id=reply.id, platform=platform_slug)
                db.add(content_perf)
            content_perf.views = 80 + index * 8
            content_perf.engagement = 8 + index
            content_perf.conversion = 1 if reply.status == "APPROVED" else 0
            content_perf.score = score_value

        strategy_specs_intel = [
            ("SEMI_AUTO", "reddit", 8, 7, 1, 87.5, 82, 4),
            ("REPLY_WARMUP", "reddit", 6, 5, 1, 83.3, 78, 3),
            ("SILENT_BROWSE", "x", 4, 3, 1, 75.0, 68, 1),
        ]
        for strategy, platform_slug, tasks_count, success, failure, success_rate, avg_score, conversion in strategy_specs_intel:
            item = db.scalar(select(StrategyPerformance).where(StrategyPerformance.strategy == strategy, StrategyPerformance.platform == platform_slug))
            if not item:
                item = StrategyPerformance(strategy=strategy, platform=platform_slug)
                db.add(item)
            item.tasks = tasks_count
            item.success = success
            item.failure = failure
            item.success_rate = success_rate
            item.average_score = avg_score
            item.conversion = conversion

        for account in accounts:
            platform = db.get(Platform, account.platform_id)
            platform_slug = platform.slug if platform else "unknown"
            item = db.scalar(select(AccountPerformance).where(AccountPerformance.account_id == account.id))
            if not item:
                item = AccountPerformance(account_id=account.id, platform=platform_slug)
                db.add(item)
            item.tasks = 5 + account.id
            item.success = 4 + (account.id % 3)
            item.failure = account.id % 2
            item.health_change = account.health_score - 100
            item.average_score = 72 + (account.id % 5) * 4

        platform_perf_specs = [
            ("reddit", 18, 88, 62, 48, 81),
            ("x", 7, 71, 35, 41, 67),
            ("facebook", 5, 64, 28, 34, 61),
        ]
        for platform_slug, tasks_count, success_rate, reply_rate, engagement_rate, avg_score in platform_perf_specs:
            item = db.scalar(select(PlatformPerformance).where(PlatformPerformance.platform == platform_slug))
            if not item:
                item = PlatformPerformance(platform=platform_slug)
                db.add(item)
            item.tasks = tasks_count
            item.success_rate = success_rate
            item.reply_rate = reply_rate
            item.engagement_rate = engagement_rate
            item.average_score = avg_score

        time_specs = [
            ("reddit", "FRI", 21, 8, 7, 87.5),
            ("reddit", "SAT", 22, 6, 5, 83.3),
            ("x", "FRI", 18, 5, 3, 60.0),
        ]
        for platform_slug, day, hour, tasks_count, success, success_rate in time_specs:
            item = db.scalar(select(TimePerformance).where(TimePerformance.platform == platform_slug, TimePerformance.day == day, TimePerformance.hour == hour))
            if not item:
                item = TimePerformance(platform=platform_slug, day=day, hour=hour)
                db.add(item)
            item.tasks = tasks_count
            item.success = success
            item.success_rate = success_rate

        recommendation_specs = [
            ("PLATFORM_STRATEGY", "Reddit evening replies are strongest", "Reddit replies around 21:00 have the highest seed score.", "HIGH", 88),
            ("ACCOUNT_STRATEGY", "Keep Windows worker for browser-heavy tasks", "Windows AI workstation has the best capability mix for Browser/TGE/AI.", "NORMAL", 82),
            ("PROMPT_FEEDBACK", "Experience-share replies perform well", "Historical approved replies favor practical experience sharing over direct promotion.", "NORMAL", 79),
        ]
        for recommendation_type, title, message, priority, score_value in recommendation_specs:
            item = db.scalar(select(IntelligenceRecommendation).where(IntelligenceRecommendation.recommendation_type == recommendation_type, IntelligenceRecommendation.title == title))
            if not item:
                item = IntelligenceRecommendation(recommendation_type=recommendation_type, title=title, message=message)
                db.add(item)
            item.message = message
            item.priority = priority
            item.score = score_value
            item.metadata_json = {"seed": True}

        reply_rows = db.scalars(select(Reply).order_by(Reply.id.asc()).limit(2)).all()
        if len(reply_rows) == 2 and not db.scalar(select(ReplySimilarity).where(ReplySimilarity.reply_id == reply_rows[0].id, ReplySimilarity.compared_reply_id == reply_rows[1].id)):
            db.add(
                ReplySimilarity(
                    reply_id=reply_rows[0].id,
                    compared_reply_id=reply_rows[1].id,
                    similarity_score=82.5,
                    method="seed_mock_embedding",
                )
            )

        experiment = db.scalar(select(Experiment).where(Experiment.experiment_id == "EXP-REPLY-001"))
        if not experiment:
            db.add(
                Experiment(
                    experiment_id="EXP-REPLY-001",
                    name="Experience Share vs Pure Help",
                    platform="reddit",
                    strategy_a="experience_share",
                    strategy_b="pure_help",
                    result={"strategy_a_score": 82, "strategy_b_score": 74},
                    winner="experience_share",
                    status="COMPLETED",
                )
            )

        for prompt_version in db.scalars(select(PromptVersion)).all():
            prompt_version.performance_score = prompt_version.performance_score or 78

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
            "27 posts including 10 X posts, 27 AI tasks, 8+ scheduler tasks, 4 accounts, "
            "4 TGE profiles, pipeline statistics, 3 LLM providers, 2 prompt templates, "
            "2 prompt versions, 4 provider routes, 5 platform weights, 2 engagement strategies, "
            "35 execution runtime demo tasks, 3 automation workers, 1 task lock, runtime metrics, "
            "1 automation alert, 4 browser sessions, 15 browser tabs, 5 engagement tasks, "
            "8+ reply tasks, 6+ submission tasks, 2 actor mappings, X Adapter seed data, intelligence performance data, "
            "recommendations, similarity detection, and 1 experiment."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
