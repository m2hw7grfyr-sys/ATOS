from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountPerformance,
    ContentPerformance,
    EngagementTask,
    ExecutionTask,
    Experiment,
    IntelligenceRecommendation,
    Platform,
    PlatformPerformance,
    Post,
    PromptVersion,
    Reply,
    ReplyTask,
    ReplyScore,
    ReplySimilarity,
    ReplyTemplate,
    ReplyTemplatePerformance,
    SchedulerTask,
    StrategyPerformance,
    TimePerformance,
    utc_now,
)


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


@dataclass
class EmbeddingResult:
    text: str
    vector: list[float]
    provider: str = "mock"


class EmbeddingService:
    def embed(self, text: str) -> EmbeddingResult:
        tokens = self._tokens(text)
        buckets = [0.0] * 16
        for token in tokens:
            buckets[hash(token) % len(buckets)] += 1.0
        norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return EmbeddingResult(text=text, vector=[round(value / norm, 6) for value in buckets])

    def similarity(self, left: str, right: str) -> float:
        left_vec = self.embed(left).vector
        right_vec = self.embed(right).vector
        return round(sum(a * b for a, b in zip(left_vec, right_vec)) * 100, 2)

    def _tokens(self, text: str) -> list[str]:
        return [token.lower() for token in text.replace("\n", " ").split() if token.strip()]


class ReplyScoreService:
    def __init__(self, db: Session):
        self.db = db

    def score_reply(self, reply: Reply) -> ReplyScore:
        post = self.db.get(Post, reply.post_id)
        content = reply.content or ""
        post_text = f"{post.title if post else ''} {post.content if post else ''}"
        relevance = self._relevance(post_text, content)
        quality = self._quality(content)
        engagement = 80 if reply.status in {"APPROVED", "CONFIRMED"} else 55 if reply.status == "GENERATED" else 40
        conversion = 70 if reply.status == "APPROVED" else 35
        risk = self._risk(content)
        score = clamp(relevance * 0.25 + quality * 0.25 + engagement * 0.2 + conversion * 0.2 + (100 - risk) * 0.1)
        existing = self.db.scalar(select(ReplyScore).where(ReplyScore.reply_id == reply.id))
        if not existing:
            existing = ReplyScore(reply_id=reply.id, post_id=reply.post_id)
            self.db.add(existing)
            self.db.flush()
        existing.relevance = round(relevance, 2)
        existing.quality = round(quality, 2)
        existing.engagement = round(engagement, 2)
        existing.conversion = round(conversion, 2)
        existing.risk = round(risk, 2)
        existing.score = round(score, 2)
        existing.reason = "Mock scoring based on overlap, length, status, and risk terms."
        return existing

    def _relevance(self, post_text: str, reply_text: str) -> float:
        post_tokens = set(EmbeddingService()._tokens(post_text))
        reply_tokens = set(EmbeddingService()._tokens(reply_text))
        if not post_tokens or not reply_tokens:
            return 50
        return clamp((len(post_tokens & reply_tokens) / max(len(post_tokens), 1)) * 180)

    def _quality(self, text: str) -> float:
        length = len(text.strip())
        if length < 40:
            return 45
        if length <= 700:
            return 82
        return 65

    def _risk(self, text: str) -> float:
        risky_terms = ["buy now", "dm me", "guaranteed", "cure", "cheap"]
        hits = sum(1 for term in risky_terms if term in text.lower())
        return clamp(hits * 22)


class IntelligenceRuntime:
    def __init__(self, db: Session):
        self.db = db
        self.embedding = EmbeddingService()
        self.reply_scorer = ReplyScoreService(db)

    def collect_performance(self) -> dict[str, Any]:
        replies = self.db.scalars(select(Reply)).all()
        for reply in replies:
            score = self.reply_scorer.score_reply(reply)
            post = self.db.get(Post, reply.post_id)
            platform = self.platform_for_post(post)
            existing = self.db.scalar(select(ContentPerformance).where(ContentPerformance.reply_id == reply.id))
            if not existing:
                existing = ContentPerformance(post_id=reply.post_id, reply_id=reply.id, platform=platform)
                self.db.add(existing)
            existing.views = max(existing.views or 0, (post.score if post else 0) + (post.comment_count if post else 0) + 20)
            existing.engagement = max(existing.engagement or 0, post.comment_count if post else 0)
            existing.conversion = 1 if reply.status == "APPROVED" else 0
            existing.score = score.score

        self.aggregate_strategy_performance()
        self.aggregate_account_performance()
        self.aggregate_platform_performance()
        self.aggregate_time_performance()
        self.update_prompt_performance()
        self.generate_recommendations()
        self.db.flush()
        return self.dashboard()

    def score_reply(self, reply_id: int) -> ReplyScore:
        reply = self.db.get(Reply, reply_id)
        if not reply:
            raise ValueError("reply not found")
        return self.reply_scorer.score_reply(reply)

    def feedback(self, payload: dict[str, Any]) -> IntelligenceRecommendation:
        title = str(payload.get("title") or "AI feedback captured")
        message = str(payload.get("message") or payload.get("feedback") or "Feedback added to prompt optimization queue.")
        recommendation = IntelligenceRecommendation(
            recommendation_type="PROMPT_FEEDBACK",
            title=title,
            message=message,
            priority=str(payload.get("priority") or "NORMAL"),
            score=float(payload.get("score") or 60),
            metadata_json={
                "successful_replies": payload.get("successful_replies", []),
                "failed_replies": payload.get("failed_replies", []),
                "prompt_version_id": payload.get("prompt_version_id"),
            },
        )
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def detect_duplicate_replies(self, threshold: float = 85) -> list[ReplySimilarity]:
        replies = self.db.scalars(select(Reply).order_by(Reply.id.asc())).all()
        results: list[ReplySimilarity] = []
        for index, reply in enumerate(replies):
            for other in replies[index + 1 :]:
                similarity = self.embedding.similarity(reply.content, other.content)
                if similarity < threshold:
                    continue
                existing = self.db.scalar(
                    select(ReplySimilarity).where(
                        ReplySimilarity.reply_id == reply.id,
                        ReplySimilarity.compared_reply_id == other.id,
                    )
                )
                if not existing:
                    existing = ReplySimilarity(reply_id=reply.id, compared_reply_id=other.id)
                    self.db.add(existing)
                    self.db.flush()
                existing.similarity_score = similarity
                existing.method = "mock_embedding"
                results.append(existing)
        return results

    def aggregate_strategy_performance(self) -> None:
        grouped: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"tasks": 0, "success": 0, "failure": 0, "score": 0, "conversion": 0})
        tasks = self.db.scalars(select(SchedulerTask)).all()
        for task in tasks:
            platform = self.platform_for_id(task.platform_id)
            strategy = str((task.payload or {}).get("strategy") or (task.payload or {}).get("mode") or task.task_type or "DEFAULT")
            key = (strategy, platform)
            item = grouped[key]
            item["tasks"] += 1
            item["success"] += 1 if task.status in {"EXECUTED", "DISPATCHED"} else 0
            item["failure"] += 1 if task.status == "FAILED" else 0
            item["conversion"] += 1 if task.reply_id else 0
            item["score"] += self.average_reply_score(task.reply_id)
        for (strategy, platform), item in grouped.items():
            record = self.db.scalar(select(StrategyPerformance).where(StrategyPerformance.strategy == strategy, StrategyPerformance.platform == platform))
            if not record:
                record = StrategyPerformance(strategy=strategy, platform=platform)
                self.db.add(record)
            total = max(int(item["tasks"]), 1)
            record.tasks = int(item["tasks"])
            record.success = int(item["success"])
            record.failure = int(item["failure"])
            record.success_rate = round((item["success"] / total) * 100, 2)
            record.average_score = round(item["score"] / total, 2)
            record.conversion = int(item["conversion"])

    def aggregate_account_performance(self) -> None:
        accounts = self.db.scalars(select(Account)).all()
        for account in accounts:
            platform = self.platform_for_id(account.platform_id)
            tasks = self.db.scalars(select(ExecutionTask).where(ExecutionTask.account_id == account.id)).all()
            total = len(tasks)
            success = sum(1 for task in tasks if task.status == "SUCCESS")
            failure = sum(1 for task in tasks if task.status == "FAILED")
            record = self.db.scalar(select(AccountPerformance).where(AccountPerformance.account_id == account.id))
            if not record:
                record = AccountPerformance(account_id=account.id, platform=platform)
                self.db.add(record)
            record.tasks = total
            record.success = success
            record.failure = failure
            record.health_change = round((account.health_score or 100) - 100, 2)
            record.average_score = round((success / max(total, 1)) * 100, 2)

    def aggregate_platform_performance(self) -> None:
        platforms = {self.platform_for_id(platform.id): platform for platform in self.db.scalars(select(Platform)).all()}
        for slug in platforms:
            tasks = self.db.scalars(select(ExecutionTask).where(ExecutionTask.platform == slug)).all()
            total = len(tasks)
            success = sum(1 for task in tasks if task.status == "SUCCESS")
            replies = self.db.scalar(select(func.count()).select_from(ReplyTask).where(ReplyTask.platform == slug)) or 0
            engagement = self.db.scalar(select(func.count()).select_from(EngagementTask).where(EngagementTask.platform == slug, EngagementTask.status == "SUCCESS")) or 0
            avg_score = self.db.scalar(select(func.coalesce(func.avg(ContentPerformance.score), 0)).where(ContentPerformance.platform == slug)) or 0
            record = self.db.scalar(select(PlatformPerformance).where(PlatformPerformance.platform == slug))
            if not record:
                record = PlatformPerformance(platform=slug)
                self.db.add(record)
            record.tasks = total
            record.success_rate = round((success / max(total, 1)) * 100, 2)
            record.reply_rate = round((replies / max(total, 1)) * 100, 2)
            record.engagement_rate = round((engagement / max(total, 1)) * 100, 2)
            record.average_score = round(float(avg_score), 2)

    def aggregate_time_performance(self) -> None:
        tasks = self.db.scalars(select(ExecutionTask).where(ExecutionTask.started_at.is_not(None))).all()
        grouped: dict[tuple[str, str, int], dict[str, int]] = defaultdict(lambda: {"tasks": 0, "success": 0})
        for task in tasks:
            started = task.started_at or utc_now()
            key = (task.platform or "unknown", started.strftime("%a").upper(), started.hour)
            grouped[key]["tasks"] += 1
            grouped[key]["success"] += 1 if task.status == "SUCCESS" else 0
        for (platform, day, hour), item in grouped.items():
            record = self.db.scalar(select(TimePerformance).where(TimePerformance.platform == platform, TimePerformance.day == day, TimePerformance.hour == hour))
            if not record:
                record = TimePerformance(platform=platform, day=day, hour=hour)
                self.db.add(record)
            record.tasks = item["tasks"]
            record.success = item["success"]
            record.success_rate = round((item["success"] / max(item["tasks"], 1)) * 100, 2)

    def update_prompt_performance(self) -> None:
        versions = self.db.scalars(select(PromptVersion)).all()
        avg_score = self.db.scalar(select(func.coalesce(func.avg(ReplyScore.score), 0))) or 0
        for version in versions:
            version.performance_score = round(float(avg_score), 2)

    def generate_recommendations(self) -> list[IntelligenceRecommendation]:
        recommendations: list[IntelligenceRecommendation] = []
        top_platform = self.db.scalar(select(PlatformPerformance).order_by(PlatformPerformance.average_score.desc()))
        if top_platform:
            recommendations.append(
                self.upsert_recommendation(
                    "PLATFORM_STRATEGY",
                    "Best platform detected",
                    f"{top_platform.platform} currently has the strongest average score.",
                    top_platform.average_score,
                    {"platform": top_platform.platform},
                )
            )
        best_time = self.db.scalar(select(TimePerformance).order_by(TimePerformance.success_rate.desc(), TimePerformance.tasks.desc()))
        if best_time:
            recommendations.append(
                self.upsert_recommendation(
                    "TIME_OPTIMIZATION",
                    "Best execution time window",
                    f"{best_time.platform} performs best on {best_time.day} at {best_time.hour}:00.",
                    best_time.success_rate,
                    {"platform": best_time.platform, "day": best_time.day, "hour": best_time.hour},
                )
            )
        weak_account = self.db.scalar(select(AccountPerformance).where(AccountPerformance.failure > 0).order_by(AccountPerformance.failure.desc()))
        if weak_account:
            recommendations.append(
                self.upsert_recommendation(
                    "ACCOUNT_STRATEGY",
                    "Reduce frequency for risky account",
                    f"Account {weak_account.account_id} has recent failures. Reduce reply frequency and increase browse-only actions.",
                    75,
                    {"account_id": weak_account.account_id},
                    priority="HIGH",
                )
            )
        best_template = self.db.scalar(
            select(ReplyTemplatePerformance)
            .where(ReplyTemplatePerformance.submitted_count > 0)
            .order_by(ReplyTemplatePerformance.success_rate.desc(), ReplyTemplatePerformance.verified_count.desc())
        )
        if best_template:
            template = self.db.get(ReplyTemplate, best_template.template_id)
            recommendations.append(
                self.upsert_recommendation(
                    "TEMPLATE_STRATEGY",
                    "Best reply template by platform",
                    f"{best_template.platform} currently performs best with {template.name_cn if template else best_template.template_id}.",
                    best_template.success_rate,
                    {"template_id": best_template.template_id, "platform": best_template.platform},
                )
            )
        return recommendations

    def dashboard(self) -> dict[str, Any]:
        return {
            "top_strategies": [self.serialize(item) for item in self.db.scalars(select(StrategyPerformance).order_by(StrategyPerformance.average_score.desc()).limit(5)).all()],
            "top_replies": [self.serialize(item) for item in self.db.scalars(select(ReplyScore).order_by(ReplyScore.score.desc()).limit(5)).all()],
            "best_accounts": [self.serialize(item) for item in self.db.scalars(select(AccountPerformance).order_by(AccountPerformance.average_score.desc()).limit(5)).all()],
            "best_time": [self.serialize(item) for item in self.db.scalars(select(TimePerformance).order_by(TimePerformance.success_rate.desc()).limit(5)).all()],
            "platform_ranking": [self.serialize(item) for item in self.db.scalars(select(PlatformPerformance).order_by(PlatformPerformance.average_score.desc()).limit(5)).all()],
            "template_performance": self.template_performance(),
            "funnel": self.funnel(),
        }

    def performance(self) -> dict[str, Any]:
        return {
            "content": [self.serialize(item) for item in self.db.scalars(select(ContentPerformance).order_by(ContentPerformance.score.desc()).limit(20)).all()],
            "strategy": [self.serialize(item) for item in self.db.scalars(select(StrategyPerformance).order_by(StrategyPerformance.average_score.desc())).all()],
            "account": [self.serialize(item) for item in self.db.scalars(select(AccountPerformance).order_by(AccountPerformance.average_score.desc())).all()],
            "platform": [self.serialize(item) for item in self.db.scalars(select(PlatformPerformance).order_by(PlatformPerformance.average_score.desc())).all()],
            "time": [self.serialize(item) for item in self.db.scalars(select(TimePerformance).order_by(TimePerformance.success_rate.desc()).limit(24)).all()],
            "templates": self.template_performance(),
        }

    def template_performance(self) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(ReplyTemplatePerformance).order_by(
                ReplyTemplatePerformance.success_rate.desc(),
                ReplyTemplatePerformance.verified_count.desc(),
            )
        ).all()
        result = []
        for row in rows:
            item = self.serialize(row)
            template = self.db.get(ReplyTemplate, row.template_id)
            item["template_name_cn"] = template.name_cn if template else None
            item["funnel_intent"] = template.funnel_intent if template else None
            item["risk_level"] = template.risk_level if template else None
            result.append(item)
        return result

    def funnel(self) -> dict[str, int]:
        return {
            "posts": self.db.scalar(select(func.count()).select_from(Post)) or 0,
            "ai_generated": self.db.scalar(select(func.count()).select_from(Reply)) or 0,
            "approved": self.db.scalar(select(func.count()).select_from(Reply).where(Reply.status == "APPROVED")) or 0,
            "executed": self.db.scalar(select(func.count()).select_from(ExecutionTask).where(ExecutionTask.status == "SUCCESS")) or 0,
            "engaged": self.db.scalar(select(func.count()).select_from(EngagementTask).where(EngagementTask.status == "SUCCESS")) or 0,
            "converted": self.db.scalar(select(func.count()).select_from(ContentPerformance).where(ContentPerformance.conversion > 0)) or 0,
        }

    def upsert_recommendation(self, recommendation_type: str, title: str, message: str, score: float, metadata: dict[str, Any], priority: str = "NORMAL") -> IntelligenceRecommendation:
        existing = self.db.scalar(select(IntelligenceRecommendation).where(IntelligenceRecommendation.recommendation_type == recommendation_type, IntelligenceRecommendation.title == title))
        if not existing:
            existing = IntelligenceRecommendation(recommendation_type=recommendation_type, title=title, message=message)
            self.db.add(existing)
        existing.message = message
        existing.score = round(score, 2)
        existing.priority = priority
        existing.metadata_json = metadata
        existing.status = "OPEN"
        return existing

    def average_reply_score(self, reply_id: int | None) -> float:
        if not reply_id:
            return 0
        return self.db.scalar(select(func.coalesce(func.avg(ReplyScore.score), 0)).where(ReplyScore.reply_id == reply_id)) or 0

    def platform_for_post(self, post: Post | None) -> str:
        return self.platform_for_id(post.platform_id) if post else "unknown"

    def platform_for_id(self, platform_id: int | None) -> str:
        platform = self.db.get(Platform, platform_id) if platform_id else None
        return platform.slug if platform else "unknown"

    def serialize(self, item: Any) -> dict[str, Any]:
        return {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in item.__dict__.items()
            if not key.startswith("_")
        }
