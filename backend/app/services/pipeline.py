from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AITask,
    AuditLog,
    BusinessEvent,
    DataSource,
    Post,
    Reply,
    SchedulerTask,
)
from app.services.ai import AIAnalysisService, ReplyGenerationService
from app.services.apify import ApifyService
from app.services.audit import write_audit
from app.services.event_bus import LocalEventBus
from app.services.scheduler import queue_approved_ai_task
from app.services.timeline import set_post_status


POST_STATUSES = [
    "NEW",
    "NORMALIZED",
    "READY_FOR_AI",
    "ANALYZING",
    "AI_COMPLETED",
    "WAITING_REVIEW",
    "APPROVED",
    "SCHEDULED",
    "ARCHIVED",
]


@dataclass
class PipelineResult:
    processed: int = 0
    analyzed: int = 0
    approved: int = 0
    rejected: int = 0
    archived: int = 0
    scheduled: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    details: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "processed": self.processed,
            "analyzed": self.analyzed,
            "approved": self.approved,
            "rejected": self.rejected,
            "archived": self.archived,
            "scheduled": self.scheduled,
            "errors": self.errors,
            "details": self.details,
        }


class BusinessPipelineService:
    def __init__(self, db: Session, actor: str = "system", trace_id: str = "system") -> None:
        self.db = db
        self.actor = actor
        self.trace_id = trace_id
        self.events = LocalEventBus()

    def run_data_source(self, data_source_id: int) -> dict[str, Any]:
        source = self.db.get(DataSource, data_source_id)
        if not source:
            raise ValueError("Data source not found")
        log = ApifyService(self.db).run(source)
        imported_posts = self.db.scalars(
            select(Post).where(
                Post.data_source_id == source.id,
                Post.status.in_(["NEW", "NORMALIZED"]),
            )
        ).all()
        for post in imported_posts:
            if post.status == "NEW":
                set_post_status(
                    self.db,
                    post,
                    "NORMALIZED",
                    event_name="PostNormalized",
                    actor=self.actor,
                    detail={"data_source_id": source.id, "crawl_log_id": log.id},
                )
            set_post_status(
                self.db,
                post,
                "READY_FOR_AI",
                event_name="PostImported",
                actor=self.actor,
                detail={"data_source_id": source.id, "crawl_log_id": log.id},
            )
        self.db.commit()
        return {
            "crawl_log_id": log.id,
            "status": log.status,
            "inserted_count": log.inserted_count,
            "duplicate_count": log.duplicate_count,
            "ready_for_ai_count": len(imported_posts),
        }

    def prepare_post(self, post_id: int) -> Post:
        post = self._get_post(post_id)
        if post.status == "NEW":
            set_post_status(self.db, post, "NORMALIZED", event_name="PostNormalized", actor=self.actor)
        if post.status in {"NORMALIZED", "INCOMPLETE"}:
            set_post_status(self.db, post, "READY_FOR_AI", event_name="PostReadyForAI", actor=self.actor)
        self.db.flush()
        return post

    def analyze_post(self, post_id: int, *, generate_reply: bool = True) -> dict[str, Any]:
        post = self.prepare_post(post_id)
        set_post_status(self.db, post, "ANALYZING", event_name="PostAnalyzing", actor=self.actor)
        self.db.commit()
        analysis = AIAnalysisService().analyze(self.db, post_id)
        reply_result = None
        if generate_reply:
            strategy = analysis["task"].strategy or "EDUCATION"
            reply_result = ReplyGenerationService().generate(
                self.db,
                post_id=post_id,
                strategy=strategy,
                tone="supportive",
                variables={"pipeline": "sprint-01"},
                task_id=analysis["task"].id,
            )
        post = self._get_post(post_id)
        set_post_status(
            self.db,
            post,
            "AI_COMPLETED",
            event_name="AICompleted",
            actor=self.actor,
            detail={"ai_task_id": analysis["task"].id},
        )
        set_post_status(
            self.db,
            post,
            "WAITING_REVIEW",
            event_name="PostWaitingReview",
            actor=self.actor,
            detail={"ai_task_id": analysis["task"].id},
        )
        self.db.commit()
        return {
            "post_id": post_id,
            "ai_task_id": analysis["task"].id,
            "reply_id": reply_result["reply"].id if reply_result else None,
            "status": post.status,
        }

    def approve_post(self, post_id: int) -> dict[str, Any]:
        post = self._get_post(post_id)
        task = self._latest_ai_task(post_id)
        reply = self._latest_reply(post_id, task.id if task else None)
        if not task or not reply:
            generated = self.analyze_post(post_id, generate_reply=True)
            task = self.db.get(AITask, generated["ai_task_id"])
            reply = self.db.get(Reply, generated["reply_id"]) if generated["reply_id"] else None
        if not task or not reply:
            raise ValueError("No AI task or reply available for approval")
        task.status = "APPROVED"
        reply.status = "APPROVED"
        set_post_status(
            self.db,
            post,
            "APPROVED",
            event_name="ReplyApproved",
            actor=self.actor,
            detail={"ai_task_id": task.id, "reply_id": reply.id},
        )
        write_audit(
            self.db,
            action="Approve",
            entity_type="Post",
            entity_uuid=post.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={"post_id": post.id, "ai_task_id": task.id, "reply_id": reply.id},
        )
        self.db.commit()
        return {"post_id": post.id, "ai_task_id": task.id, "reply_id": reply.id, "status": post.status}

    def reject_post(self, post_id: int) -> dict[str, Any]:
        post = self._get_post(post_id)
        task = self._latest_ai_task(post_id)
        reply = self._latest_reply(post_id, task.id if task else None)
        if task:
            task.status = "REJECTED"
        if reply:
            reply.status = "REJECTED"
        write_audit(
            self.db,
            action="Reject",
            entity_type="Post",
            entity_uuid=post.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={"post_id": post.id, "ai_task_id": task.id if task else None},
        )
        self.events.publish(
            self.db,
            "ReplyRejected",
            entity_type="Post",
            entity_id=post.id,
            post_id=post.id,
            payload={"ai_task_id": task.id if task else None},
        )
        self.db.commit()
        return {"post_id": post.id, "status": post.status, "ai_task_id": task.id if task else None}

    def archive_post(self, post_id: int) -> dict[str, Any]:
        post = self._get_post(post_id)
        set_post_status(self.db, post, "ARCHIVED", event_name="PostArchived", actor=self.actor)
        write_audit(
            self.db,
            action="Archive",
            entity_type="Post",
            entity_uuid=post.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={"post_id": post.id},
        )
        self.db.commit()
        return {"post_id": post.id, "status": post.status}

    def send_to_scheduler(self, post_id: int, *, priority: str = "MEDIUM") -> dict[str, Any]:
        post = self._get_post(post_id)
        task = self._latest_ai_task(post_id)
        if not task or task.status != "APPROVED":
            approved = self.approve_post(post_id)
            task = self.db.get(AITask, approved["ai_task_id"])
        if not task:
            raise ValueError("No approved AI task available")
        scheduler_task = queue_approved_ai_task(
            self.db,
            ai_task_id=task.id,
            priority=priority,
            source="PIPELINE",
        )
        set_post_status(
            self.db,
            post,
            "SCHEDULED",
            event_name="TaskScheduled",
            actor=self.actor,
            detail={"ai_task_id": task.id, "scheduler_task_id": scheduler_task.id},
        )
        write_audit(
            self.db,
            action="Schedule",
            entity_type="Post",
            entity_uuid=post.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={"post_id": post.id, "scheduler_task_id": scheduler_task.id},
        )
        self.db.commit()
        return {
            "post_id": post.id,
            "ai_task_id": task.id,
            "scheduler_task_id": scheduler_task.id,
            "status": post.status,
        }

    def run_post(
        self,
        post_id: int,
        *,
        auto_approve: bool = False,
        send_to_scheduler: bool = False,
    ) -> dict[str, Any]:
        result = self.analyze_post(post_id, generate_reply=True)
        if auto_approve:
            result.update(self.approve_post(post_id))
        if send_to_scheduler:
            result.update(self.send_to_scheduler(post_id))
        return result

    def batch(self, post_ids: list[int], action: str, *, priority: str = "MEDIUM") -> dict[str, Any]:
        action_key = action.upper()
        result = PipelineResult()
        for post_id in post_ids:
            try:
                if action_key == "ANALYZE":
                    detail = self.analyze_post(post_id)
                    result.analyzed += 1
                elif action_key == "APPROVE":
                    detail = self.approve_post(post_id)
                    result.approved += 1
                elif action_key == "REJECT":
                    detail = self.reject_post(post_id)
                    result.rejected += 1
                elif action_key == "ARCHIVE":
                    detail = self.archive_post(post_id)
                    result.archived += 1
                elif action_key in {"SEND_TO_SCHEDULER", "SCHEDULE"}:
                    detail = self.send_to_scheduler(post_id, priority=priority)
                    result.scheduled += 1
                else:
                    raise ValueError(f"Unsupported pipeline action: {action}")
                result.processed += 1
                result.details.append(detail)
            except Exception as exc:
                self.db.rollback()
                result.errors.append({"post_id": post_id, "error": str(exc)})
        return result.as_dict()

    def status(self) -> dict[str, Any]:
        status_counts = {
            status: self.db.scalar(
                select(func.count()).select_from(Post).where(Post.status == status)
            )
            or 0
            for status in POST_STATUSES
        }
        scheduled = self.db.scalar(select(func.count()).select_from(SchedulerTask)) or 0
        approved = status_counts.get("APPROVED", 0) + status_counts.get("SCHEDULED", 0)
        imported = self.db.scalar(select(func.count()).select_from(Post)) or 0
        events = self.db.scalar(select(func.count()).select_from(BusinessEvent)) or 0
        audits = self.db.scalar(select(func.count()).select_from(AuditLog)) or 0
        success_base = max(imported, 1)
        return {
            "post_status": status_counts,
            "imported": imported,
            "ai_completed": status_counts.get("AI_COMPLETED", 0) + status_counts.get("WAITING_REVIEW", 0) + approved,
            "approved": approved,
            "scheduled": scheduled,
            "events": events,
            "audit_logs": audits,
            "pipeline_success_rate": round((scheduled / success_base) * 100, 2),
        }

    def _get_post(self, post_id: int) -> Post:
        post = self.db.get(Post, post_id)
        if not post:
            raise ValueError("Post not found")
        return post

    def _latest_ai_task(self, post_id: int) -> AITask | None:
        return self.db.scalar(
            select(AITask)
            .where(AITask.post_id == post_id)
            .order_by(AITask.updated_at.desc(), AITask.id.desc())
        )

    def _latest_reply(self, post_id: int, ai_task_id: int | None = None) -> Reply | None:
        statement = select(Reply).where(Reply.post_id == post_id)
        if ai_task_id is not None:
            statement = statement.where(Reply.ai_task_id == ai_task_id)
        return self.db.scalar(statement.order_by(Reply.version.desc(), Reply.id.desc()))
