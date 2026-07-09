from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request

from app.database import get_db
from app.models import AITask, Account, DataSource, Platform, Post, SchedulerTask
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
                    SchedulerTask, SchedulerTask.status.in_(["QUEUED", "DELAYED"])
                ),
                "active_accounts": count(Account, Account.status == "ACTIVE"),
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
