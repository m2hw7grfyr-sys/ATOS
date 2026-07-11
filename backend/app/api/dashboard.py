from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request

from app.database import get_db
from app.models import AIGenerationLog, AITask, Account, BrowserSession, BrowserTab, ContentPerformance, DataSource, EngagementTask, ExecutionQueue, ExecutionTask, IntelligenceRecommendation, LLMProvider, Platform, PlatformRegistry, Post, Reply, ReplyScore, ReplyTask, SchedulerTask, StatisticSnapshot, SubmissionTask, SystemAlert, TGEProfile, TimePerformance, WorkerNode
from app.response import ok
from app.services.submission_runtime import SubmissionRuntime


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(request: Request, db: Session = Depends(get_db)):
    def count(model, *filters):
        statement = select(func.count()).select_from(model)
        if filters:
            statement = statement.where(*filters)
        return db.scalar(statement) or 0

    platforms = db.scalars(select(Platform).order_by(Platform.name)).all()
    platform_registry = db.scalars(select(PlatformRegistry).order_by(PlatformRegistry.platform_name)).all()
    def metric_value(metric: str) -> float:
        return db.scalar(
            select(func.coalesce(func.sum(StatisticSnapshot.value), 0)).where(
                StatisticSnapshot.metric == metric,
                StatisticSnapshot.period == "TODAY",
            )
        ) or 0

    total_ai_logs = count(AIGenerationLog)
    fallback_logs = count(AIGenerationLog, AIGenerationLog.fallback_used.is_(True))
    avg_latency = db.scalar(select(func.coalesce(func.avg(AIGenerationLog.provider_latency_ms), 0))) or 0
    ai_cost = db.scalar(select(func.coalesce(func.sum(AIGenerationLog.estimated_cost), 0))) or 0
    healthy_providers = count(LLMProvider, LLMProvider.health_status.in_(["HEALTHY", "UNKNOWN"]))
    unhealthy_providers = count(LLMProvider, LLMProvider.health_status.in_(["WARNING", "ERROR", "DISABLED"]))
    today_imported = metric_value("pipeline_import")
    today_ai = metric_value("pipeline_ai")
    pipeline_approved = count(Post, Post.status.in_(["APPROVED", "SCHEDULED"]))
    pipeline_scheduled = count(Post, Post.status == "SCHEDULED")
    pipeline_total = count(Post)
    pipeline_success_rate = round((pipeline_scheduled / max(pipeline_total, 1)) * 100, 2)
    submission_overview = SubmissionRuntime(db).dashboard_counts()

    return ok(
        {
            "overview": {
                "posts": count(Post),
                "ai_pending": count(
                    AITask,
                    AITask.status.in_(
                        [
                            "PENDING",
                            "ANALYZING",
                            "ANALYZED",
                            "GENERATING",
                            "GENERATED",
                            "REVIEWING",
                            "FALLBACK_USED",
                            "NEW",
                        ]
                    ),
                ),
                "scheduler_queue": count(
                    SchedulerTask, SchedulerTask.status.in_(["NEW", "QUEUED", "DELAYED"])
                ),
                "scheduler_pending": count(
                    SchedulerTask, SchedulerTask.status.in_(["NEW", "QUEUED", "WAITING_ACCOUNT", "WAITING_TIME"])
                ),
                "scheduler_ready": count(SchedulerTask, SchedulerTask.status == "READY"),
                "scheduler_delayed": count(SchedulerTask, SchedulerTask.status == "DELAYED"),
                "scheduler_failed": count(SchedulerTask, SchedulerTask.status == "FAILED"),
                "no_available_account": count(SchedulerTask, SchedulerTask.status == "WAITING_ACCOUNT"),
                "active_accounts": count(Account, Account.status == "ACTIVE"),
                "cooling_accounts": count(Account, Account.risk_status == "COOLING_DOWN"),
                "high_risk_accounts": count(Account, Account.risk_status.in_(["HIGH", "CRITICAL"])),
                "tge_profiles_active": count(TGEProfile, TGEProfile.status == "ACTIVE"),
                "execution_received": count(ExecutionTask, ExecutionTask.status == "RECEIVED"),
                "execution_environment_ready": count(ExecutionTask, ExecutionTask.status == "ENVIRONMENT_READY"),
                "execution_failed": count(ExecutionTask, ExecutionTask.status == "FAILED"),
                "execution_queue": count(ExecutionQueue, ExecutionQueue.status == "QUEUED"),
                "execution_workers": count(WorkerNode, WorkerNode.status == "ONLINE"),
                "worker_online": count(WorkerNode, WorkerNode.status == "ONLINE"),
                "worker_offline": count(WorkerNode, WorkerNode.status == "OFFLINE"),
                "worker_avg_cpu": round(float(db.scalar(select(func.coalesce(func.avg(WorkerNode.cpu), 0))) or 0), 2),
                "worker_avg_memory": round(float(db.scalar(select(func.coalesce(func.avg(WorkerNode.memory), 0))) or 0), 2),
                "worker_avg_gpu": round(float(db.scalar(select(func.coalesce(func.avg(WorkerNode.gpu), 0))) or 0), 2),
                "worker_running_tasks": count(ExecutionTask, ExecutionTask.status.in_(["CLAIMED", "RUNNING", "WAITING_MANUAL"])),
                "worker_capacity": db.scalar(select(func.coalesce(func.sum(WorkerNode.max_concurrent_tasks), 0)).where(WorkerNode.status == "ONLINE")) or 0,
                "automation_retry_pending": count(ExecutionTask, ExecutionTask.status == "RETRY_PENDING"),
                "automation_worker_lost": count(ExecutionTask, ExecutionTask.status == "WORKER_LOST"),
                "automation_alerts": count(SystemAlert, SystemAlert.status == "OPEN"),
                "automation_queue_length": count(ExecutionQueue, ExecutionQueue.status.in_(["QUEUED", "RETRY_PENDING"])),
                "intelligence_recommendations": count(IntelligenceRecommendation, IntelligenceRecommendation.status == "OPEN"),
                "reply_average_score": round(float(db.scalar(select(func.coalesce(func.avg(ReplyScore.score), 0))) or 0), 2),
                "content_average_score": round(float(db.scalar(select(func.coalesce(func.avg(ContentPerformance.score), 0))) or 0), 2),
                "best_time_windows": count(TimePerformance, TimePerformance.success_rate > 0),
                "execution_running": count(ExecutionTask, ExecutionTask.status == "RUNNING"),
                "execution_success": count(ExecutionTask, ExecutionTask.status == "SUCCESS"),
                "browser_running": count(BrowserSession, BrowserSession.status.in_(["RUNNING", "ATTACHED"])),
                "browser_tabs_open": count(BrowserTab, BrowserTab.status == "OPEN"),
                "browser_dead_sessions": count(BrowserSession, BrowserSession.status == "BROKEN"),
                "tge_connection_failed": count(TGEProfile, TGEProfile.connection_status == "FAILED"),
                "tge_running": count(TGEProfile, TGEProfile.runtime_status == "RUNNING"),
                "tge_unknown": count(TGEProfile, TGEProfile.runtime_status == "UNKNOWN"),
                "accounts_without_tge": count(
                    Account,
                    Account.status == "ACTIVE",
                    ~Account.id.in_(
                        select(TGEProfile.bound_account_id).where(TGEProfile.bound_account_id.is_not(None))
                    ),
                ),
                "data_sources": count(DataSource, DataSource.enabled.is_(True)),
                "today_browse": metric_value("browse_count"),
                "today_like": metric_value("like_count"),
                "today_profile_visit": metric_value("visit_profile_count"),
                "warmup_tasks": count(EngagementTask, EngagementTask.status.in_(["NEW", "QUEUED", "RUNNING", "WAITING_EXECUTION"])),
                "engagement_success_rate": metric_value("engagement_success_rate"),
                "llm_provider_health": f"{healthy_providers} healthy / {unhealthy_providers} attention",
                "fallback_rate": round((fallback_logs / total_ai_logs) * 100, 2) if total_ai_logs else 0,
                "average_latency_ms": round(float(avg_latency), 2),
                "ai_cost_today": round(float(ai_cost), 6),
                "pipeline_today_imported": today_imported or count(Post),
                "pipeline_today_ai": today_ai or count(Post, Post.status.in_(["AI_COMPLETED", "WAITING_REVIEW", "APPROVED", "SCHEDULED"])),
                "pipeline_approved": pipeline_approved,
                "pipeline_scheduled": pipeline_scheduled,
                "pipeline_success_rate": pipeline_success_rate,
                "reply_ai_generated": count(Reply, Reply.status.in_(["GENERATED", "APPROVED"])),
                "reply_waiting_review": count(Reply, Reply.status == "GENERATED"),
                "reply_scheduled": count(ReplyTask, ReplyTask.status == "SCHEDULED"),
                "reply_executing": count(ReplyTask, ReplyTask.status == "EXECUTING"),
                "reply_waiting_manual": count(ReplyTask, ReplyTask.status == "WAITING_MANUAL"),
                "reply_completed": count(ReplyTask, ReplyTask.status == "CONFIRMED"),
                "reply_failed": count(ReplyTask, ReplyTask.status == "FAILED"),
                "submission_ready": count(SubmissionTask, SubmissionTask.status == "PREPARED"),
                "submission_waiting_manual": count(SubmissionTask, SubmissionTask.status == "WAITING_MANUAL"),
                "submission_submitting": count(SubmissionTask, SubmissionTask.status == "VERIFYING"),
                "submission_verified": count(SubmissionTask, SubmissionTask.status == "VERIFIED"),
                "submission_failed": count(SubmissionTask, SubmissionTask.status == "FAILED"),
                "submission_manual_required": count(
                    SubmissionTask, SubmissionTask.status == "MANUAL_REQUIRED"
                ),
                **submission_overview,
                "active_platforms": count(PlatformRegistry, PlatformRegistry.enabled.is_(True)),
                "healthy_platforms": count(PlatformRegistry, PlatformRegistry.status.in_(["HEALTHY", "UNKNOWN"])),
                "failed_adapters": count(PlatformRegistry, PlatformRegistry.status.in_(["ERROR", "FAILED"])),
            },
            "platform_health": [
                {
                    "name": registry.platform_name.title(),
                    "slug": registry.platform_name,
                    "status": registry.status,
                    "enabled": registry.enabled,
                    "adapter": registry.adapter_name,
                    "version": registry.version,
                    "capabilities": registry.capabilities or [],
                }
                for registry in platform_registry
            ]
            or [
                {
                    "name": platform.name,
                    "slug": platform.slug,
                    "status": platform.status,
                    "enabled": platform.enabled,
                }
                for platform in platforms
            ],
            "system_health": [
                {"service": "API", "status": "HEALTHY"},
                {"service": "Database", "status": "HEALTHY"},
                {"service": "Scheduler", "status": "READY"},
                {"service": "Execution", "status": "PLACEHOLDER"},
            ],
        },
        request.state.trace_id,
    )
