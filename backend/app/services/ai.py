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
    Platform,
    Post,
    PromptTemplate,
    PromptVersion,
    ProviderRouting,
    Reply,
    utc_now,
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
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


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
            input_tokens=token_estimate(prompt),
            output_tokens=token_estimate(text),
            estimated_cost=0.0,
        )

    def generate_analysis(self, *, prompt: str, post: Post, **kwargs: Any) -> ProviderResult:
        return self.generate(purpose="analysis", prompt=prompt, post=post, **kwargs)

    def generate_reply(self, *, prompt: str, post: Post, **kwargs: Any) -> ProviderResult:
        return self.generate(purpose="reply", prompt=prompt, post=post, **kwargs)

    def generate_embedding(self, *, text: str, **_: Any) -> ProviderResult:
        return ProviderResult(
            text=json.dumps({"embedding_dimensions": 0, "mock": True}),
            provider_used=self.provider_name,
            model_used=self.model_name,
            generation_source="MOCK",
            input_tokens=token_estimate(text),
            output_tokens=1,
            estimated_cost=0.0,
        )

    def validate_config(self) -> tuple[bool, str | None]:
        return True, None

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    def health_check(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "message": "Mock provider is always available."}


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
                usage = payload.get("usage") or {}
                input_tokens = int(usage.get("prompt_tokens") or token_estimate(prompt))
                output_tokens = int(usage.get("completion_tokens") or token_estimate(text))
                return ProviderResult(
                    text=text,
                    provider_used=self.provider.provider_name,
                    model_used=self.provider.model_name,
                    generation_source="LLM",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost=self.estimate_cost(input_tokens, output_tokens),
                )
            except (KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError) as exc:
                last_error = exc
                time.sleep(0.25)
        raise AIProviderError(f"OpenAI provider failed: {last_error}")

    def generate_analysis(self, *, prompt: str, post: Post, **kwargs: Any) -> ProviderResult:
        return self.generate(purpose="analysis", prompt=prompt, post=post, **kwargs)

    def generate_reply(self, *, prompt: str, post: Post, **kwargs: Any) -> ProviderResult:
        return self.generate(purpose="reply", prompt=prompt, post=post, **kwargs)

    def generate_embedding(self, *, text: str, **_: Any) -> ProviderResult:
        if not self.provider.api_key:
            raise AIProviderError("OpenAI provider api_key is not configured")
        input_tokens = token_estimate(text)
        return ProviderResult(
            text=json.dumps({"embedding_dimensions": 0, "not_implemented": True}),
            provider_used=self.provider.provider_name,
            model_used=self.provider.model_name,
            generation_source="LLM",
            input_tokens=input_tokens,
            output_tokens=1,
            estimated_cost=self.estimate_cost(input_tokens, 1),
        )

    def validate_config(self) -> tuple[bool, str | None]:
        if not self.provider.api_key:
            return False, "api_key is not configured"
        if not self.provider.model_name:
            return False, "model_name is not configured"
        return True, None

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Conservative placeholder until model-specific price tables are configured.
        return round((input_tokens + output_tokens) * 0.000001, 6)

    def health_check(self) -> dict[str, Any]:
        valid, error = self.validate_config()
        if not valid:
            return {"status": "WARNING", "message": error}
        return {"status": "HEALTHY", "message": "Provider configuration is valid."}


class ConfigurableProvider:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate(self, *, purpose: str, prompt: str, post: Post, **_: Any) -> ProviderResult:
        if self.provider.provider_type in {"anthropic", "gemini", "ollama", "custom_http", "custom"}:
            if not self.provider.api_base_url and self.provider.provider_type in {"ollama", "custom_http", "custom"}:
                raise AIProviderError(f"{self.provider.provider_type} api_base_url is not configured")
            if self.provider.provider_type in {"anthropic", "gemini", "custom_http", "custom"} and not self.provider.api_key:
                raise AIProviderError(f"{self.provider.provider_type} api_key is not configured")
        raise AIProviderError(f"{self.provider.provider_type} runtime adapter is not implemented yet")

    def generate_analysis(self, *, prompt: str, post: Post, **kwargs: Any) -> ProviderResult:
        return self.generate(purpose="analysis", prompt=prompt, post=post, **kwargs)

    def generate_reply(self, *, prompt: str, post: Post, **kwargs: Any) -> ProviderResult:
        return self.generate(purpose="reply", prompt=prompt, post=post, **kwargs)

    def generate_embedding(self, *, text: str, **_: Any) -> ProviderResult:
        raise AIProviderError(f"{self.provider.provider_type} embedding adapter is not implemented yet")

    def validate_config(self) -> tuple[bool, str | None]:
        if self.provider.provider_type in {"custom_http", "custom", "ollama"} and not self.provider.api_base_url:
            return False, "api_base_url is not configured"
        if self.provider.provider_type in {"anthropic", "gemini", "custom_http", "custom"} and not self.provider.api_key:
            return False, "api_key is not configured"
        return True, None

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return round((input_tokens + output_tokens) * 0.000001, 6)

    def health_check(self) -> dict[str, Any]:
        valid, error = self.validate_config()
        return {
            "status": "HEALTHY" if valid else "WARNING",
            "message": "Provider configuration is valid." if valid else error,
        }


def provider_adapter(provider: LLMProvider | None):
    if not provider or provider.is_mock or provider.provider_type == "mock":
        return MockProvider()
    if provider.provider_type == "openai":
        return OpenAIProvider(provider)
    return ConfigurableProvider(provider)


def provider_is_usable(provider: LLMProvider | None) -> bool:
    if not provider or not provider.enabled:
        return False
    adapter = provider_adapter(provider)
    valid, _ = adapter.validate_config()
    return valid


def select_provider(db: Session, purpose: str) -> LLMProvider | None:
    purpose_column = (
        LLMProvider.use_for_analysis if purpose == "analysis" else LLMProvider.use_for_reply
    )
    return db.scalar(
        select(LLMProvider)
        .where(LLMProvider.enabled.is_(True), purpose_column.is_(True))
        .order_by(LLMProvider.priority.asc(), LLMProvider.id.asc())
    )


def select_fallback_provider(db: Session, preferred: LLMProvider | None = None) -> LLMProvider | None:
    query = (
        select(LLMProvider)
        .where(LLMProvider.enabled.is_(True))
        .order_by(LLMProvider.is_mock.asc(), LLMProvider.priority.asc(), LLMProvider.id.asc())
    )
    for provider in db.scalars(query).all():
        if preferred and provider.id == preferred.id:
            continue
        if provider_is_usable(provider):
            return provider
    return None


def get_platform_slug(db: Session, post: Post) -> str | None:
    if not post.platform_id:
        return None
    platform = db.get(Platform, post.platform_id)
    return platform.slug if platform else None


def select_provider_route(
    db: Session,
    *,
    post: Post,
    task_type: str,
    strategy: str | None,
    commercial_score: int = 0,
    risk_score: int = 0,
) -> tuple[LLMProvider | None, LLMProvider | None, ProviderRouting | None]:
    platform = get_platform_slug(db, post)
    routes = db.scalars(
        select(ProviderRouting)
        .where(ProviderRouting.enabled.is_(True), ProviderRouting.task_type == task_type.upper())
        .order_by(ProviderRouting.priority.asc(), ProviderRouting.id.asc())
    ).all()
    for route in routes:
        platform_match = route.platform in (None, "", platform)
        strategy_match = route.strategy in (None, "", strategy)
        score_match = commercial_score >= route.min_commercial_score and risk_score <= route.max_risk_score
        if not (platform_match and strategy_match and score_match):
            continue
        preferred = db.get(LLMProvider, route.preferred_provider_id) if route.preferred_provider_id else None
        fallback = db.get(LLMProvider, route.fallback_provider_id) if route.fallback_provider_id else None
        if preferred and preferred.enabled:
            return preferred, fallback if provider_is_usable(fallback) else select_fallback_provider(db, preferred), route
        if provider_is_usable(fallback):
            return fallback, select_fallback_provider(db, fallback), route
    provider = select_provider(db, "analysis" if task_type.upper() == "ANALYSIS" else "reply")
    if provider and provider.enabled:
        return provider, select_fallback_provider(db, provider), None
    return select_fallback_provider(db), None, None


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


def get_prompt_version(
    db: Session,
    *,
    template: PromptTemplate | None,
    platform: str | None,
    strategy: str | None,
    tone: str | None,
) -> PromptVersion | None:
    if not template:
        return None
    versions = db.scalars(
        select(PromptVersion)
        .where(PromptVersion.prompt_template_id == template.id, PromptVersion.enabled.is_(True))
        .order_by(PromptVersion.is_default.desc(), PromptVersion.id.desc())
    ).all()
    for version in versions:
        platform_match = version.platform in (None, "", platform)
        strategy_match = version.strategy in (None, "", strategy)
        tone_match = version.tone in (None, "", tone)
        if platform_match and strategy_match and tone_match:
            return version
    return versions[0] if versions else None


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
    prompt_version_id: int | None = None,
    strategy: str | None = None,
) -> ProviderResult:
    task_type = "ANALYSIS" if purpose == "analysis" else "REPLY"
    commercial = ai_task.commercial_score if ai_task else 0
    risk = ai_task.risk_score if ai_task else 0
    provider, fallback_provider, _route = select_provider_route(
        db,
        post=post,
        task_type=task_type,
        strategy=strategy,
        commercial_score=commercial,
        risk_score=risk,
    )
    attempts: list[tuple[LLMProvider | None, str]] = [
        (provider, "primary"),
        (fallback_provider, "fallback"),
        (None, "mock"),
    ]
    errors: list[str] = []
    first_provider_name = provider.provider_name if provider else "Mock Provider"
    for selected_provider, step in attempts:
        started = time.perf_counter()
        adapter = provider_adapter(selected_provider)
        try:
            result = (
                adapter.generate_analysis(prompt=prompt, post=post)
                if purpose == "analysis"
                else adapter.generate_reply(prompt=prompt, post=post)
            )
            if step != "primary":
                result.fallback_used = True
                result.generation_source = "FALLBACK" if step != "mock" else "MOCK"
            duration = int((time.perf_counter() - started) * 1000)
            input_tokens = result.input_tokens or token_estimate(prompt)
            output_tokens = result.output_tokens or token_estimate(result.text)
            total_tokens = input_tokens + output_tokens
            db.add(
                AIGenerationLog(
                    post_id=post.id,
                    ai_task_id=ai_task.id if ai_task else None,
                    provider=result.provider_used,
                    model=result.model_used,
                    prompt_version=prompt_version,
                    prompt_version_id=prompt_version_id,
                    purpose=purpose.upper(),
                    duration_ms=duration,
                    token_estimate=total_tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=result.estimated_cost,
                    provider_latency_ms=duration,
                    generation_source=result.generation_source,
                    fallback_used=result.fallback_used,
                    fallback_reason="; ".join(errors) if result.fallback_used else None,
                    fallback_from_provider=first_provider_name if result.fallback_used else None,
                    fallback_to_provider=result.provider_used if result.fallback_used else None,
                    status="SUCCESS",
                )
            )
            if ai_task:
                ai_task.provider_id = selected_provider.id if selected_provider else None
                ai_task.fallback_provider_id = fallback_provider.id if fallback_provider else None
                ai_task.prompt_version_id = prompt_version_id
                ai_task.generation_source = result.generation_source
                ai_task.fallback_used = result.fallback_used
                ai_task.fallback_reason = "; ".join(errors) if result.fallback_used else None
            return result
        except AIProviderError as exc:
            error_message = str(exc)
            errors.append(f"{step}: {error_message}")
            failed_duration = int((time.perf_counter() - started) * 1000)
            selected_name = selected_provider.provider_name if selected_provider else "Mock Provider"
            db.add(
                AIGenerationLog(
                    post_id=post.id,
                    ai_task_id=ai_task.id if ai_task else None,
                    provider=selected_name,
                    model=selected_provider.model_name if selected_provider else "mock-v0.3",
                    prompt_version=prompt_version,
                    prompt_version_id=prompt_version_id,
                    purpose=purpose.upper(),
                    duration_ms=failed_duration,
                    token_estimate=token_estimate(prompt),
                    input_tokens=token_estimate(prompt),
                    output_tokens=0,
                    total_tokens=token_estimate(prompt),
                    estimated_cost=0.0,
                    provider_latency_ms=failed_duration,
                    generation_source="LLM" if selected_provider else "MOCK",
                    fallback_used=True,
                    fallback_reason=error_message,
                    fallback_from_provider=selected_name,
                    fallback_to_provider=None,
                    status="FAILED",
                    error_message=error_message,
                )
            )

    fallback_started = time.perf_counter()
    result = MockProvider().generate(purpose=purpose, prompt=prompt, post=post)
    result.fallback_used = True
    result.generation_source = "TEMPLATE"
    db.add(
        AIGenerationLog(
            post_id=post.id,
            ai_task_id=ai_task.id if ai_task else None,
            provider=result.provider_used,
            model=result.model_used,
            prompt_version=prompt_version,
            prompt_version_id=prompt_version_id,
            purpose=purpose.upper(),
            duration_ms=int((time.perf_counter() - fallback_started) * 1000),
            token_estimate=token_estimate(prompt, result.text),
            input_tokens=token_estimate(prompt),
            output_tokens=token_estimate(result.text),
            total_tokens=token_estimate(prompt, result.text),
            estimated_cost=0.0,
            provider_latency_ms=int((time.perf_counter() - fallback_started) * 1000),
            generation_source="FALLBACK",
            fallback_used=True,
            fallback_reason="; ".join(errors) or "manual template fallback",
            fallback_from_provider=first_provider_name,
            fallback_to_provider=result.provider_used,
            status="SUCCESS",
            error_message="; ".join(errors),
        )
    )
    return result


def preview_prompt(
    db: Session,
    *,
    task_id: int,
    strategy: str = "PURE_HELP",
    tone: str = "supportive",
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task = db.get(AITask, task_id)
    if not task:
        raise AIProviderError("AI task not found")
    post = db.get(Post, task.post_id)
    if not post:
        raise AIProviderError("post not found")
    platform = get_platform_slug(db, post)
    template = get_prompt_template(
        db,
        template_type="reply_prompt",
        platform=platform,
        strategy=strategy,
        tone=tone,
    )
    version = get_prompt_version(db, template=template, platform=platform, strategy=strategy, tone=tone)
    content = version.content if version else (template.content if template else DEFAULT_REPLY_PROMPT)
    rendered_variables = {
        "strategy": strategy,
        "tone": tone,
        "variables": json.dumps(variables or {}, ensure_ascii=False),
    }
    final_prompt = render_prompt(content, post, **rendered_variables)
    return {
        "system_prompt": "You are an ATOS AI workspace provider. Return concise, useful output.",
        "platform_prompt": f"Platform: {platform or 'generic'}",
        "strategy_prompt": f"Strategy: {strategy}",
        "variables": rendered_variables,
        "prompt_template_id": template.id if template else None,
        "prompt_version_id": version.id if version else None,
        "prompt_version": version.version if version else (template.version if template else "fallback"),
        "final_prompt": final_prompt,
    }


def test_provider_config(db: Session, provider: LLMProvider) -> dict[str, Any]:
    adapter = provider_adapter(provider)
    health = adapter.health_check()
    provider.health_status = health["status"]
    provider.last_health_check_at = utc_now()
    provider.last_health_error = None if health["status"] == "HEALTHY" else health.get("message")
    db.commit()
    db.refresh(provider)
    return {
        "provider_id": provider.id,
        "provider_name": provider.provider_name,
        "provider_type": provider.provider_type,
        "health_status": provider.health_status,
        "message": health.get("message"),
        "api_key_configured": bool(provider.api_key),
    }


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
        platform = get_platform_slug(db, post)
        template = get_prompt_template(
            db,
            template_type="analysis_prompt",
            platform=platform,
            strategy=None,
            tone=None,
        )
        version = get_prompt_version(db, template=template, platform=platform, strategy=None, tone=None)
        prompt_version = version.version if version else (template.version if template else "v0.3")
        prompt = render_prompt(
            version.content if version else (template.content if template else DEFAULT_ANALYSIS_PROMPT),
            post,
        )
        result = call_provider(
            db,
            post=post,
            purpose="analysis",
            prompt=prompt,
            ai_task=task,
            prompt_version=prompt_version,
            prompt_version_id=version.id if version else None,
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
        task.prompt_version_id = version.id if version else None
        task.strategy = analysis.recommended_strategy or "PURE_HELP"
        task.commercial_score = analysis.commercial_score
        task.risk_score = analysis.risk_score
        task.result = analysis.raw_result
        task.generation_source = result.generation_source
        task.fallback_used = result.fallback_used
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
        platform = get_platform_slug(db, post)
        template = get_prompt_template(
            db,
            template_type="reply_prompt",
            platform=platform,
            strategy=strategy,
            tone=tone,
        )
        version = get_prompt_version(db, template=template, platform=platform, strategy=strategy, tone=tone)
        prompt_version = version.version if version else (template.version if template else "v0.3")
        prompt = render_prompt(
            version.content if version else (template.content if template else DEFAULT_REPLY_PROMPT),
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
            prompt_version_id=version.id if version else None,
            strategy=strategy,
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
        task.prompt_version_id = version.id if version else None
        task.strategy = strategy.upper()
        task.generation_source = result.generation_source
        task.fallback_used = result.fallback_used
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
