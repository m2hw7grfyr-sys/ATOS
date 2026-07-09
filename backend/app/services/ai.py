from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AIAnalysisResult,
    AIGenerationLog,
    AITask,
    LLMProvider,
    Post,
    PromptTemplate,
    Reply,
)


class AIProviderError(RuntimeError):
    pass


@dataclass
class ProviderResult:
    text: str
    provider_used: str
    model_used: str
    generation_source: str
    fallback_used: bool = False


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"


def token_estimate(*parts: str) -> int:
    text = " ".join(parts)
    return max(1, len(text) // 4)


def safe_json_parse(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return None
    return None


class MockProvider:
    provider_name = "Mock Provider"
    provider_type = "mock"
    model_name = "mock-v0.3"

    def generate(self, *, purpose: str, prompt: str, post: Post, **_: Any) -> ProviderResult:
        if purpose == "analysis":
            lower_text = f"{post.title} {post.content}".lower()
            intent = "QUESTION" if "?" in post.title or "how" in lower_text else "DISCUSSION"
            strategy = "PURE_HELP" if intent == "QUESTION" else "EXPERIENCE_SHARE"
            payload = {
                "intent": intent,
                "pain_point": "Needs a practical next step without heavy tooling.",
                "commercial_score": 72 if "tool" in lower_text or "automation" in lower_text else 58,
                "risk_score": 12,
                "recommended_strategy": strategy,
                "summary": f"Mock analysis for: {post.title}",
            }
            text = json.dumps(payload, ensure_ascii=False)
        else:
            text = (
                f"I'd start with one small, repeatable step for this: {post.title}. "
                "Write down the current friction, try one lightweight change for a week, "
                "then keep only what actually reduces effort."
            )
        return ProviderResult(
            text=text,
            provider_used=self.provider_name,
            model_used=self.model_name,
            generation_source="MOCK",
        )


class OpenAIProvider:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate(self, *, purpose: str, prompt: str, post: Post, **_: Any) -> ProviderResult:
        if not self.provider.api_key:
            raise AIProviderError("OpenAI provider api_key is not configured")
        base_url = (self.provider.api_base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        body = {
            "model": self.provider.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an ATOS AI workspace provider. Return concise, useful output.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
        if purpose == "analysis":
            body["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.provider.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        attempts = max(1, self.provider.max_retries + 1)
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.provider.timeout_seconds
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                text = payload["choices"][0]["message"]["content"]
                return ProviderResult(
                    text=text,
                    provider_used=self.provider.provider_name,
                    model_used=self.provider.model_name,
                    generation_source="LLM",
                )
            except (KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError) as exc:
                last_error = exc
                time.sleep(0.25)
        raise AIProviderError(f"OpenAI provider failed: {last_error}")


def select_provider(db: Session, purpose: str) -> LLMProvider | None:
    purpose_column = (
        LLMProvider.use_for_analysis if purpose == "analysis" else LLMProvider.use_for_reply
    )
    return db.scalar(
        select(LLMProvider)
        .where(LLMProvider.enabled.is_(True), purpose_column.is_(True))
        .order_by(LLMProvider.priority.asc(), LLMProvider.id.asc())
    )


def get_prompt_template(
    db: Session, *, template_type: str, platform: str | None, strategy: str | None, tone: str | None
) -> PromptTemplate | None:
    query = (
        select(PromptTemplate)
        .where(
            PromptTemplate.enabled.is_(True),
            PromptTemplate.template_type == template_type,
        )
        .order_by(PromptTemplate.id.asc())
    )
    templates = db.scalars(query).all()
    for template in templates:
        platform_match = template.platform in (None, "", platform)
        strategy_match = template.strategy in (None, "", strategy)
        tone_match = template.tone in (None, "", tone)
        if platform_match and strategy_match and tone_match:
            return template
    return templates[0] if templates else None


def render_prompt(template: str, post: Post, **extra: Any) -> str:
    values = {
        "title": post.title or "",
        "content": post.content or "",
        "community": post.community or "",
        "author": post.author or "",
        "url": post.url or "",
        **{key: str(value) for key, value in extra.items()},
    }
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def call_provider(
    db: Session,
    *,
    post: Post,
    purpose: str,
    prompt: str,
    ai_task: AITask | None,
    prompt_version: str,
) -> ProviderResult:
    provider = select_provider(db, purpose)
    real_provider_error: str | None = None
    started = time.perf_counter()
    try:
        if provider and not provider.is_mock and provider.provider_type == "openai":
            result = OpenAIProvider(provider).generate(
                purpose=purpose, prompt=prompt, post=post
            )
        else:
            result = MockProvider().generate(purpose=purpose, prompt=prompt, post=post)
        duration = int((time.perf_counter() - started) * 1000)
        db.add(
            AIGenerationLog(
                post_id=post.id,
                ai_task_id=ai_task.id if ai_task else None,
                provider=result.provider_used,
                model=result.model_used,
                prompt_version=prompt_version,
                purpose=purpose.upper(),
                duration_ms=duration,
                token_estimate=token_estimate(prompt, result.text),
                generation_source=result.generation_source,
                fallback_used=result.fallback_used,
                status="SUCCESS",
            )
        )
        return result
    except AIProviderError as exc:
        real_provider_error = str(exc)
        failed_duration = int((time.perf_counter() - started) * 1000)
        db.add(
            AIGenerationLog(
                post_id=post.id,
                ai_task_id=ai_task.id if ai_task else None,
                provider=provider.provider_name if provider else "none",
                model=provider.model_name if provider else "none",
                prompt_version=prompt_version,
                purpose=purpose.upper(),
                duration_ms=failed_duration,
                token_estimate=token_estimate(prompt),
                generation_source="LLM",
                fallback_used=True,
                status="FAILED",
                error_message=real_provider_error,
            )
        )

    fallback_started = time.perf_counter()
    result = MockProvider().generate(purpose=purpose, prompt=prompt, post=post)
    result.fallback_used = True
    result.generation_source = "FALLBACK"
    db.add(
        AIGenerationLog(
            post_id=post.id,
            ai_task_id=ai_task.id if ai_task else None,
            provider=result.provider_used,
            model=result.model_used,
            prompt_version=prompt_version,
            purpose=purpose.upper(),
            duration_ms=int((time.perf_counter() - fallback_started) * 1000),
            token_estimate=token_estimate(prompt, result.text),
            generation_source="FALLBACK",
            fallback_used=True,
            status="SUCCESS",
            error_message=real_provider_error,
        )
    )
    return result


class AIAnalysisService:
    def analyze(self, db: Session, post_id: int) -> dict[str, Any]:
        post = db.get(Post, post_id)
        if not post:
            raise AIProviderError("post not found")
        task = db.scalar(select(AITask).where(AITask.post_id == post.id).order_by(AITask.id.desc()))
        if not task:
            task = AITask(
                post_id=post.id,
                provider="pending",
                model="pending",
                strategy="PENDING",
                status="PENDING",
            )
            db.add(task)
            db.flush()
        task.status = "ANALYZING"
        template = get_prompt_template(
            db,
            template_type="analysis_prompt",
            platform=None,
            strategy=None,
            tone=None,
        )
        prompt_version = template.version if template else "v0.3"
        prompt = render_prompt(
            template.content if template else DEFAULT_ANALYSIS_PROMPT,
            post,
        )
        result = call_provider(
            db,
            post=post,
            purpose="analysis",
            prompt=prompt,
            ai_task=task,
            prompt_version=prompt_version,
        )
        parsed = safe_json_parse(result.text) or {}
        analysis = AIAnalysisResult(
            post_id=post.id,
            ai_task_id=task.id,
            intent=str(parsed.get("intent", "UNKNOWN")),
            pain_point=str(parsed.get("pain_point", "")),
            commercial_score=int(parsed.get("commercial_score", 50) or 0),
            risk_score=int(parsed.get("risk_score", 10) or 0),
            recommended_strategy=str(parsed.get("recommended_strategy", "PURE_HELP")),
            summary=str(parsed.get("summary", result.text[:500])),
            provider_used=result.provider_used,
            model_used=result.model_used,
            generation_source=result.generation_source,
            raw_result=parsed or {"text": result.text},
        )
        db.add(analysis)
        task.provider = result.provider_used
        task.model = result.model_used
        task.strategy = analysis.recommended_strategy or "PURE_HELP"
        task.commercial_score = analysis.commercial_score
        task.risk_score = analysis.risk_score
        task.result = analysis.raw_result
        task.status = "FALLBACK_USED" if result.fallback_used else "ANALYZED"
        post.status = "ANALYZED"
        db.commit()
        db.refresh(task)
        db.refresh(analysis)
        return {"task": task, "analysis": analysis}


class ReplyGenerationService:
    def generate(
        self,
        db: Session,
        *,
        post_id: int,
        strategy: str = "PURE_HELP",
        tone: str = "supportive",
        variables: dict[str, Any] | None = None,
        task_id: int | None = None,
    ) -> dict[str, Any]:
        post = db.get(Post, post_id)
        if not post:
            raise AIProviderError("post not found")
        task = db.get(AITask, task_id) if task_id else None
        if not task:
            task = db.scalar(select(AITask).where(AITask.post_id == post.id).order_by(AITask.id.desc()))
        if not task:
            task = AITask(
                post_id=post.id,
                provider="pending",
                model="pending",
                strategy=strategy.upper(),
                status="PENDING",
            )
            db.add(task)
            db.flush()
        task.status = "GENERATING"
        template = get_prompt_template(
            db,
            template_type="reply_prompt",
            platform=None,
            strategy=strategy,
            tone=tone,
        )
        prompt_version = template.version if template else "v0.3"
        prompt = render_prompt(
            template.content if template else DEFAULT_REPLY_PROMPT,
            post,
            strategy=strategy,
            tone=tone,
            variables=json.dumps(variables or {}, ensure_ascii=False),
        )
        result = call_provider(
            db,
            post=post,
            purpose="reply",
            prompt=prompt,
            ai_task=task,
            prompt_version=prompt_version,
        )
        existing_versions = db.scalars(select(Reply).where(Reply.ai_task_id == task.id)).all()
        reply = Reply(
            post_id=post.id,
            ai_task_id=task.id,
            content=result.text,
            source=result.generation_source,
            version=len(existing_versions) + 1,
            status="GENERATED",
        )
        db.add(reply)
        task.provider = result.provider_used
        task.model = result.model_used
        task.strategy = strategy.upper()
        task.status = "FALLBACK_USED" if result.fallback_used else "GENERATED"
        db.commit()
        db.refresh(task)
        db.refresh(reply)
        return {"task": task, "reply": reply, "fallback_used": result.fallback_used}


DEFAULT_ANALYSIS_PROMPT = """Analyze this post and return JSON only:
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
"""

DEFAULT_REPLY_PROMPT = """Write a helpful, non-spammy reply draft.
Strategy: {{strategy}}
Tone: {{tone}}
Variables: {{variables}}

Title: {{title}}
Content: {{content}}
Community: {{community}}
"""
