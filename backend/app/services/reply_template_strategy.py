from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AITask,
    Platform,
    PlatformTemplateRule,
    Post,
    ReplyTask,
    ReplyTemplate,
    ReplyTemplatePerformance,
)
from app.services.audit import write_audit


FUNNEL_INTENTS = {
    "NO_CTA",
    "PROFILE_CTA",
    "MAIN_ACCOUNT_CTA",
    "DIRECT_LINK_CTA",
    "TRUST_BUILDING",
    "THREAD_CTA",
    "BIO_CTA",
    "DM_CTA",
}
CTA_STRENGTHS = {"NONE", "SOFT", "MEDIUM", "STRONG"}
HIGH_RISK_LEVELS = {"HIGH", "CRITICAL"}


BUILT_IN_REPLY_TEMPLATES: list[dict[str, Any]] = [
    {
        "name_cn": "纯帮助，不引流",
        "name_en": "Pure Help No CTA",
        "description": "只回答问题，不提主页、链接、产品或私信。",
        "funnel_intent": "NO_CTA",
        "cta_strength": "NONE",
        "risk_level": "LOW",
        "default_platforms": ["reddit", "x", "facebook", "instagram", "tiktok"],
    },
    {
        "name_cn": "软引导主页",
        "name_en": "Soft Profile CTA",
        "description": "先完整回答，结尾只允许轻提示主页或置顶内容。",
        "funnel_intent": "PROFILE_CTA",
        "cta_strength": "SOFT",
        "risk_level": "LOW_MEDIUM",
        "default_platforms": ["reddit", "x", "facebook", "instagram"],
    },
    {
        "name_cn": "引导到大号",
        "name_en": "Main Account CTA",
        "description": "自然提到主账号、thread 或长期内容资产，避免过度营销。",
        "funnel_intent": "MAIN_ACCOUNT_CTA",
        "cta_strength": "MEDIUM",
        "risk_level": "MEDIUM",
        "default_platforms": ["x", "facebook", "instagram"],
    },
    {
        "name_cn": "直接外链",
        "name_en": "Direct Link CTA",
        "description": "直接引导到外链，只在平台规则允许时使用。",
        "funnel_intent": "DIRECT_LINK_CTA",
        "cta_strength": "STRONG",
        "risk_level": "HIGH",
        "default_platforms": ["x"],
    },
    {
        "name_cn": "不引导，信任建设",
        "name_en": "Trust Building No CTA",
        "description": "真实互动、共情、经验和补充信息，目标是建立信任。",
        "funnel_intent": "TRUST_BUILDING",
        "cta_strength": "NONE",
        "risk_level": "LOW",
        "default_platforms": ["reddit", "x", "facebook", "instagram", "tiktok"],
    },
]


PLATFORM_RULES: dict[str, dict[str, dict[str, Any]]] = {
    "reddit": {
        "NO_CTA": {"allowed": True, "default_enabled": True, "max_daily_ratio": 1.0, "risk_level": "LOW", "allow_auto_assisted": True},
        "PROFILE_CTA": {"allowed": True, "default_enabled": True, "max_daily_ratio": 0.3, "risk_level": "LOW_MEDIUM", "allow_auto_assisted": True},
        "MAIN_ACCOUNT_CTA": {"allowed": True, "default_enabled": False, "max_daily_ratio": 0.1, "risk_level": "MEDIUM", "allow_auto_assisted": False},
        "DIRECT_LINK_CTA": {"allowed": False, "default_enabled": False, "max_daily_ratio": 0.0, "risk_level": "HIGH", "allow_auto_assisted": False},
        "TRUST_BUILDING": {"allowed": True, "default_enabled": True, "max_daily_ratio": 1.0, "risk_level": "LOW", "allow_auto_assisted": True},
    },
    "x": {
        "NO_CTA": {"allowed": True, "default_enabled": True, "max_daily_ratio": 1.0, "risk_level": "LOW", "allow_auto_assisted": True},
        "PROFILE_CTA": {"allowed": True, "default_enabled": True, "max_daily_ratio": 0.4, "risk_level": "LOW_MEDIUM", "allow_auto_assisted": True},
        "MAIN_ACCOUNT_CTA": {"allowed": True, "default_enabled": True, "max_daily_ratio": 0.3, "risk_level": "MEDIUM", "allow_auto_assisted": True},
        "DIRECT_LINK_CTA": {"allowed": True, "default_enabled": False, "max_daily_ratio": 0.15, "risk_level": "HIGH", "allow_auto_assisted": False},
        "TRUST_BUILDING": {"allowed": True, "default_enabled": True, "max_daily_ratio": 1.0, "risk_level": "LOW", "allow_auto_assisted": True},
    },
}


CONSERVATIVE_PLATFORMS = ["facebook", "instagram", "tiktok"]


TEMPLATE_PROMPT_INSTRUCTIONS: dict[str, str] = {
    "NO_CTA": "模板：纯帮助，不引流。只回答问题；不提主页；不提链接；不提产品；不引导私信。",
    "PROFILE_CTA": "模板：软引导主页。先完整回答；结尾只允许轻提示主页或置顶内容；不要直接放外链。",
    "MAIN_ACCOUNT_CTA": "模板：引导到大号。适用于 X；可自然提到主账号或 thread；不要过度营销。",
    "DIRECT_LINK_CTA": "模板：直接外链。只在平台规则允许时使用；自然说明链接价值；禁止夸张营销语言。",
    "TRUST_BUILDING": "模板：不引导，信任建设。只做真实互动；重点是共情、经验和补充信息。",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TemplateSelection:
    selected_template_id: int
    reason: str
    risk_level: str
    cta_allowed: bool
    rule: PlatformTemplateRule | None
    template: ReplyTemplate


def ensure_reply_template_seed(db: Session) -> None:
    templates: dict[str, ReplyTemplate] = {}
    for spec in BUILT_IN_REPLY_TEMPLATES:
        item = db.scalar(select(ReplyTemplate).where(ReplyTemplate.funnel_intent == spec["funnel_intent"]))
        if not item:
            item = ReplyTemplate(**spec)
            db.add(item)
            db.flush()
        else:
            for key, value in spec.items():
                if key not in {"funnel_intent", "enabled"}:
                    setattr(item, key, value)
        templates[item.funnel_intent] = item

    platforms = {**PLATFORM_RULES}
    conservative = {
        "NO_CTA": {"allowed": True, "default_enabled": True, "max_daily_ratio": 1.0, "risk_level": "LOW", "allow_auto_assisted": True},
        "PROFILE_CTA": {"allowed": True, "default_enabled": False, "max_daily_ratio": 0.15, "risk_level": "LOW_MEDIUM", "allow_auto_assisted": False},
        "MAIN_ACCOUNT_CTA": {"allowed": False, "default_enabled": False, "max_daily_ratio": 0.0, "risk_level": "MEDIUM", "allow_auto_assisted": False},
        "DIRECT_LINK_CTA": {"allowed": False, "default_enabled": False, "max_daily_ratio": 0.0, "risk_level": "HIGH", "allow_auto_assisted": False},
        "TRUST_BUILDING": {"allowed": True, "default_enabled": True, "max_daily_ratio": 1.0, "risk_level": "LOW", "allow_auto_assisted": True},
    }
    for platform in CONSERVATIVE_PLATFORMS:
        platforms[platform] = conservative

    for platform, rules in platforms.items():
        for intent, rule_spec in rules.items():
            template = templates.get(intent)
            if not template:
                continue
            rule = db.scalar(
                select(PlatformTemplateRule).where(
                    PlatformTemplateRule.platform == platform,
                    PlatformTemplateRule.template_id == template.id,
                )
            )
            values = {**rule_spec, "notes": f"Seed rule for {platform} / {template.name_cn}"}
            if not rule:
                db.add(PlatformTemplateRule(platform=platform, template_id=template.id, **values))
    db.flush()


def platform_slug_for_post(db: Session, post: Post | None, fallback: str | None = None) -> str:
    if post and post.platform_id:
        platform = db.get(Platform, post.platform_id)
        if platform:
            return platform.slug
    return str(fallback or "reddit").lower()


def template_instruction(template: ReplyTemplate | None) -> str:
    if not template:
        return TEMPLATE_PROMPT_INSTRUCTIONS["NO_CTA"]
    return TEMPLATE_PROMPT_INSTRUCTIONS.get(template.funnel_intent, TEMPLATE_PROMPT_INSTRUCTIONS["NO_CTA"])


class TemplateSelectionEngine:
    def __init__(self, db: Session, *, actor: str = "operator", trace_id: str = "system") -> None:
        self.db = db
        self.actor = actor
        self.trace_id = trace_id
        ensure_reply_template_seed(db)

    def select(
        self,
        *,
        platform: str,
        post_score: int = 0,
        risk_score: int = 0,
        account_age_level: str | None = None,
        account_health: int = 100,
        community_rule_level: str | None = None,
        historical_success_rate: float = 0,
        operator_preference: int | None = None,
    ) -> TemplateSelection:
        platform = platform.lower()
        if operator_preference:
            preferred = self.db.get(ReplyTemplate, operator_preference)
            if preferred:
                rule = self.rule_for(platform, preferred.id)
                if rule and rule.allowed and self.ratio_available(platform, preferred, rule):
                    return TemplateSelection(preferred.id, "Operator selected allowed template.", rule.risk_level, True, rule, preferred)

        intent = "NO_CTA"
        reason = "Defaulted to pure help for safe first contact."
        if risk_score >= 60 or community_rule_level in {"STRICT", "HIGH"}:
            intent = "TRUST_BUILDING"
            reason = "High platform/community risk; selected trust building."
        elif platform == "x" and post_score >= 70 and account_health >= 80:
            intent = "MAIN_ACCOUNT_CTA"
            reason = "X allows main-account CTA for strong-fit posts."
        elif risk_score <= 25 and post_score >= 65 and account_health >= 75:
            intent = "PROFILE_CTA"
            reason = "Low risk and good fit; selected soft profile CTA."

        selected = self.template_by_intent(intent) or self.template_by_intent("NO_CTA")
        rule = self.rule_for(platform, selected.id)
        if not rule or not rule.allowed or not self.ratio_available(platform, selected, rule):
            fallback = self.safe_template(platform)
            fallback_rule = self.rule_for(platform, fallback.id)
            return TemplateSelection(
                fallback.id,
                f"{reason} Downgraded to {fallback.name_cn} due to platform rule or daily ratio.",
                fallback_rule.risk_level if fallback_rule else fallback.risk_level,
                bool(fallback_rule and fallback_rule.allowed),
                fallback_rule,
                fallback,
            )
        return TemplateSelection(selected.id, reason, rule.risk_level, True, rule, selected)

    def apply_to_reply_task(self, task: ReplyTask, selection: TemplateSelection) -> ReplyTask:
        template = selection.template
        rule = selection.rule
        task.reply_template_id = template.id
        task.funnel_intent = template.funnel_intent
        task.cta_strength = template.cta_strength
        task.template_selection_reason = selection.reason
        task.link_allowed = template.funnel_intent in {"DIRECT_LINK_CTA"} and bool(rule and rule.allowed)
        task.profile_redirect_allowed = template.funnel_intent == "PROFILE_CTA" and bool(rule and rule.allowed)
        task.main_account_redirect_allowed = template.funnel_intent == "MAIN_ACCOUNT_CTA" and bool(rule and rule.allowed)
        task.direct_link_allowed = template.funnel_intent == "DIRECT_LINK_CTA" and bool(rule and rule.allowed)
        return task

    def validate_approval(self, task: ReplyTask) -> tuple[bool, str]:
        if not task.reply_template_id:
            return False, "Reply task has no selected template."
        rule = self.rule_for(str(task.platform or "").lower(), task.reply_template_id)
        if not rule or not rule.allowed:
            return False, "Platform rule does not allow this template."
        template = self.db.get(ReplyTemplate, task.reply_template_id)
        if not template or not template.enabled:
            return False, "Template is disabled."
        if not self.ratio_available(str(task.platform or "").lower(), template, rule):
            return False, "Template daily ratio exceeded."
        return True, "Template approval guard passed."

    def auto_assisted_allowed(self, task: ReplyTask) -> tuple[bool, str]:
        if not task.reply_template_id:
            return False, "AUTO_ASSISTED requires a selected reply template."
        template = self.db.get(ReplyTemplate, task.reply_template_id)
        rule = self.rule_for(str(task.platform or "").lower(), task.reply_template_id)
        if not template or not rule:
            return False, "Template or platform rule missing."
        if template.risk_level in HIGH_RISK_LEVELS or rule.risk_level in HIGH_RISK_LEVELS:
            return False, "High-risk templates require manual submission."
        if not rule.allow_auto_assisted:
            return False, "Platform rule disables AUTO_ASSISTED for this template."
        return True, "Template is eligible for AUTO_ASSISTED."

    def record_performance(self, task: ReplyTask, field: str, amount: int = 1) -> None:
        if not task.reply_template_id or not task.platform:
            return
        today = utc_now().date().isoformat()
        item = self.db.scalar(
            select(ReplyTemplatePerformance).where(
                ReplyTemplatePerformance.template_id == task.reply_template_id,
                ReplyTemplatePerformance.platform == task.platform,
                ReplyTemplatePerformance.date == today,
            )
        )
        if not item:
            item = ReplyTemplatePerformance(template_id=task.reply_template_id, platform=task.platform, date=today)
            self.db.add(item)
            self.db.flush()
        if hasattr(item, field):
            setattr(item, field, int(getattr(item, field) or 0) + amount)
        submitted = max(int(item.submitted_count or 0), 1)
        item.success_rate = round((int(item.verified_count or 0) / submitted) * 100, 2)
        item.failure_rate = round((int(item.failed_count or 0) / submitted) * 100, 2)

    def performance(self) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(ReplyTemplatePerformance).order_by(ReplyTemplatePerformance.date.desc())).all()
        result = []
        for row in rows:
            template = self.db.get(ReplyTemplate, row.template_id)
            result.append(
                {
                    "id": row.id,
                    "template_id": row.template_id,
                    "template_name_cn": template.name_cn if template else None,
                    "funnel_intent": template.funnel_intent if template else None,
                    "platform": row.platform,
                    "date": row.date,
                    "generated_count": row.generated_count,
                    "approved_count": row.approved_count,
                    "submitted_count": row.submitted_count,
                    "verified_count": row.verified_count,
                    "failed_count": row.failed_count,
                    "engagement_count": row.engagement_count,
                    "conversion_count": row.conversion_count,
                    "success_rate": row.success_rate,
                    "failure_rate": row.failure_rate,
                }
            )
        return result

    def dashboard(self) -> dict[str, Any]:
        today = utc_now().date().isoformat()
        today_rows = self.db.scalars(select(ReplyTemplatePerformance).where(ReplyTemplatePerformance.date == today)).all()
        high_risk_ids = [
            row.id for row in self.db.scalars(select(ReplyTemplate).where(ReplyTemplate.risk_level.in_(["HIGH", "CRITICAL"]))).all()
        ]
        total_generated = sum(row.generated_count for row in today_rows)
        total_verified = sum(row.verified_count for row in today_rows)
        total_submitted = sum(row.submitted_count for row in today_rows)
        return {
            "template_generated_today": total_generated,
            "template_verified_today": total_verified,
            "template_success_rate": round((total_verified / max(total_submitted, 1)) * 100, 2),
            "high_risk_template_usage": sum(row.generated_count for row in today_rows if row.template_id in high_risk_ids),
            "template_platforms": len({row.platform for row in today_rows}),
        }

    def template_by_intent(self, intent: str) -> ReplyTemplate | None:
        return self.db.scalar(select(ReplyTemplate).where(ReplyTemplate.funnel_intent == intent, ReplyTemplate.enabled.is_(True)))

    def safe_template(self, platform: str) -> ReplyTemplate:
        return self.template_by_intent("NO_CTA") or self.db.scalar(select(ReplyTemplate).order_by(ReplyTemplate.id.asc()))

    def rule_for(self, platform: str, template_id: int) -> PlatformTemplateRule | None:
        return self.db.scalar(
            select(PlatformTemplateRule).where(
                PlatformTemplateRule.platform == platform.lower(),
                PlatformTemplateRule.template_id == template_id,
            )
        )

    def ratio_available(self, platform: str, template: ReplyTemplate, rule: PlatformTemplateRule) -> bool:
        if rule.max_daily_ratio >= 1:
            return True
        if rule.max_daily_ratio <= 0:
            return False
        today = utc_now().date()
        total = self.db.scalar(
            select(func.count()).select_from(ReplyTask).where(
                ReplyTask.platform == platform,
                func.date(ReplyTask.created_at) == today,
            )
        ) or 0
        used = self.db.scalar(
            select(func.count()).select_from(ReplyTask).where(
                ReplyTask.platform == platform,
                ReplyTask.reply_template_id == template.id,
                func.date(ReplyTask.created_at) == today,
            )
        ) or 0
        if total < 5:
            return True
        return (used / max(total, 1)) <= rule.max_daily_ratio

    def audit_template_change(
        self,
        *,
        task: ReplyTask,
        old_template_id: int | None,
        new_template_id: int | None,
        action: str,
        reason: str,
    ) -> None:
        write_audit(
            self.db,
            action=action,
            entity_type="ReplyTask",
            entity_uuid=task.uuid,
            actor=self.actor,
            trace_id=self.trace_id,
            detail={
                "reply_task_id": task.id,
                "platform": task.platform,
                "old_template_id": old_template_id,
                "new_template_id": new_template_id,
                "reason": reason,
            },
        )
