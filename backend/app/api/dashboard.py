from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request

from app.database import get_db
from app.models import AITask, Account, DataSource, ExecutionTask, Platform, Post, SchedulerTask, TGEProfile
from app.response import ok


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(request: Request, db: Session = Depends(get_db)):
    def count(model, *filters):
        statement = select(func.count()).select_from(model)
        if filters:
            statement = statement.where(*filters)
        return db.scalar(statement) or 0

    platforms = db.scalars(select(Platform).order_by(Platform.name)).all()
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
            },
            "platform_health": [
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
