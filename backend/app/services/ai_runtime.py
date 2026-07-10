from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIGenerationLog, AITask, LLMProvider, Post, utc_now
from app.services.ai import (
    AIProviderError,
    ConfigurableProvider,
    MockProvider,
    OpenAIProvider,
    call_provider,
    get_platform_slug,
    get_prompt_template,
    get_prompt_version,
    mask_secret,
    provider_adapter,
    render_prompt,
    safe_json_parse,
    select_provider_route,
    token_estimate,
)


TASK_TYPE_ANALYSIS = "ANALYSIS"
TASK_TYPE_REPLY = "REPLY_GENERATION"
TASK_TYPE_REWRITE = "REWRITE"
TASK_TYPE_EMBEDDING = "EMBEDDING"
TASK_TYPE_CLASSIFICATION = "CLASSIFICATION"
TASK_TYPE_SUMMARY = "SUMMARY"


@dataclass
class PromptContext:
    strategy: str | None = None
    tone: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    history_context: str | None = None
    role_prompt: str | None = None


@dataclass
class AIRequest:
    request_id: str
    task_type: str
    post_id: int | None = None
    platform: str | None = None
    strategy: str | None = None
    prompt_context: PromptContext = field(default_factory=PromptContext)
    preferred_provider: int | str | None = None
    fallback_enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    ai_task_id: int | None = None


@dataclass
class AIResponse:
    success: bool
    content: str = ""
    json_content: dict[str, Any] | None = None
    provider_used: str | None = None
    model_used: str | None = None
    generation_source: str | None = None
    fallback_used: bool = False
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    prompt_template_id: int | None = None
    prompt_version_id: int | None = None
    final_prompt_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "json_content": self.json_content,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "generation_source": self.generation_source,
            "fallback_used": self.fallback_used,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": self.estimated_cost,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "prompt_template_id": self.prompt_template_id,
            "prompt_version_id": self.prompt_version_id,
            "final_prompt_hash": self.final_prompt_hash,
        }


class ProviderAdapter(ABC):
    @abstractmethod
    def generate_text(self, *, prompt: str, post: Post) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, *, prompt: str, post: Post) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_embedding(self, *, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def validate_config(self) -> tuple[bool, str | None]:
        raise NotImplementedError


class RuntimeProviderAdapter(ProviderAdapter):
    def __init__(self, provider: LLMProvider | None):
        self.provider = provider
        self.adapter = provider_adapter(provider)

    def generate_text(self, *, prompt: str, post: Post) -> str:
        if isinstance(self.adapter, MockProvider):
            return self.adapter.generate_reply(prompt=prompt, post=post).text
        if isinstance(self.adapter, OpenAIProvider):
            return self.adapter.generate_reply(prompt=prompt, post=post).text
        if isinstance(self.adapter, ConfigurableProvider):
            return self.adapter.generate_reply(prompt=prompt, post=post).text
        return self.adapter.generate_reply(prompt=prompt, post=post).text

    def generate_json(self, *, prompt: str, post: Post) -> dict[str, Any]:
        text = self.adapter.generate_analysis(prompt=prompt, post=post).text
        return safe_json_parse(text) or {"text": text}

    def generate_embedding(self, *, text: str) -> list[float]:
        result = self.adapter.generate_embedding(text=text)
        parsed = safe_json_parse(result.text) or {}
        values = parsed.get("embedding")
        return values if isinstance(values, list) else []

    def health_check(self) -> dict[str, Any]:
        return self.adapter.health_check()

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return self.adapter.estimate_cost(input_tokens, output_tokens)

    def validate_config(self) -> tuple[bool, str | None]:
        return self.adapter.validate_config()


class ProviderRouter:
    def __init__(self, db: Session):
        self.db = db

    def route(self, request: AIRequest, post: Post, ai_task: AITask | None = None) -> tuple[LLMProvider | None, LLMProvider | None]:
        commercial = ai_task.commercial_score if ai_task else int(request.metadata.get("commercial_score", 0) or 0)
        risk = ai_task.risk_score if ai_task else int(request.metadata.get("risk_score", 0) or 0)
        route_task_type = request.task_type
        provider, fallback, _route = select_provider_route(
            self.db,
            post=post,
            task_type=route_task_type,
            strategy=request.strategy or request.prompt_context.strategy,
            commercial_score=commercial,
            risk_score=risk,
        )
        if request.preferred_provider:
            if isinstance(request.preferred_provider, int):
                preferred = self.db.get(LLMProvider, request.preferred_provider)
            else:
                preferred = self.db.scalar(
                    select(LLMProvider).where(LLMProvider.provider_name == str(request.preferred_provider))
                )
            if preferred and preferred.enabled:
                provider = preferred
        return provider, fallback


class PromptEngine:
    def __init__(self, db: Session):
        self.db = db

    def build(self, request: AIRequest, post: Post) -> dict[str, Any]:
        platform = request.platform or get_platform_slug(self.db, post)
        template_type = self._template_type(request.task_type)
        strategy = request.strategy or request.prompt_context.strategy
        tone = request.prompt_context.tone
        template = get_prompt_template(
            self.db,
            template_type=template_type,
            platform=platform,
            strategy=strategy,
            tone=tone,
        )
        version = get_prompt_version(
            self.db,
            template=template,
            platform=platform,
            strategy=strategy,
            tone=tone,
        )
        content = version.content if version else (template.content if template else self._fallback_template(request.task_type))
        variables = {
            "strategy": strategy or "",
            "tone": tone or "",
            "variables": json.dumps(request.prompt_context.variables or {}, ensure_ascii=False),
            "role_prompt": request.prompt_context.role_prompt or "",
            "history_context": request.prompt_context.history_context or "",
        }
        final_prompt = render_prompt(content, post, **variables)
        return {
            "system_prompt": "You are an ATOS AI Runtime provider. Return useful output and follow the requested format.",
            "platform_prompt": f"Platform: {platform or 'generic'}",
            "strategy_prompt": f"Strategy: {strategy or 'default'}",
            "role_prompt": request.prompt_context.role_prompt,
            "variables": variables,
            "post_content": {
                "title": post.title,
                "content": post.content,
                "community": post.community,
                "author": post.author,
                "url": post.url,
            },
            "history_context": request.prompt_context.history_context,
            "prompt_template_id": template.id if template else None,
            "prompt_version_id": version.id if version else None,
            "prompt_version": version.version if version else (template.version if template else "fallback"),
            "final_prompt": final_prompt,
            "final_prompt_hash": hashlib.sha256(final_prompt.encode("utf-8")).hexdigest(),
        }

    def _template_type(self, task_type: str) -> str:
        if task_type == TASK_TYPE_ANALYSIS:
            return "analysis_prompt"
        if task_type in {TASK_TYPE_REPLY, TASK_TYPE_REWRITE}:
            return "reply_prompt"
        return "analysis_prompt"

    def _fallback_template(self, task_type: str) -> str:
        if task_type == TASK_TYPE_ANALYSIS:
            return "Analyze this post and return JSON: {{title}} {{content}}"
        return "Write a helpful reply for this post: {{title}} {{content}}"


class AIRuntime:
    def __init__(self, db: Session):
        self.db = db
        self.router = ProviderRouter(db)
        self.prompt_engine = PromptEngine(db)

    def generate_analysis(self, request: AIRequest) -> AIResponse:
        return self.generate(request)

    def generate_reply(self, request: AIRequest) -> AIResponse:
        return self.generate(request)

    def generate_embedding(self, request: AIRequest) -> AIResponse:
        post = self._post(request)
        started = time.perf_counter()
        provider, _fallback = self.router.route(request, post)
        adapter = RuntimeProviderAdapter(provider)
        text = f"{post.title}\n{post.content}"
        try:
            embedding = adapter.generate_embedding(text=text)
            latency_ms = int((time.perf_counter() - started) * 1000)
            self._log_embedding(request, post, provider, latency_ms, text)
            return AIResponse(
                success=True,
                content=json.dumps({"embedding_dimensions": len(embedding), "mock": not embedding}),
                json_content={"embedding_dimensions": len(embedding), "mock": not embedding},
                provider_used=provider.provider_name if provider else "Mock Provider",
                model_used=provider.model_name if provider else "mock-v0.3",
                generation_source="LLM" if provider else "MOCK",
                fallback_used=provider is None,
                latency_ms=latency_ms,
                input_tokens=token_estimate(text),
                output_tokens=1,
                estimated_cost=0.0,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return AIResponse(False, error_code="EMBEDDING_FAILED", error_message=str(exc), latency_ms=latency_ms)

    def generate(self, request: AIRequest) -> AIResponse:
        post = self._post(request)
        ai_task = self.db.get(AITask, request.ai_task_id) if request.ai_task_id else None
        prompt_payload = self.prompt_engine.build(request, post)
        started = time.perf_counter()
        purpose = "analysis" if request.task_type in {TASK_TYPE_ANALYSIS, TASK_TYPE_CLASSIFICATION, TASK_TYPE_SUMMARY} else "reply"
        try:
            result = call_provider(
                self.db,
                post=post,
                purpose=purpose,
                prompt=prompt_payload["final_prompt"],
                ai_task=ai_task,
                prompt_version=prompt_payload["prompt_version"],
                prompt_version_id=prompt_payload["prompt_version_id"],
                prompt_template_id=prompt_payload["prompt_template_id"],
                final_prompt_hash=prompt_payload["final_prompt_hash"],
                strategy=request.strategy or request.prompt_context.strategy,
                task_type=request.task_type,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            json_content = safe_json_parse(result.text) if purpose == "analysis" else None
            return AIResponse(
                success=True,
                content=result.text,
                json_content=json_content,
                provider_used=result.provider_used,
                model_used=result.model_used,
                generation_source=result.generation_source,
                fallback_used=result.fallback_used,
                latency_ms=latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost=result.estimated_cost,
                prompt_template_id=prompt_payload["prompt_template_id"],
                prompt_version_id=prompt_payload["prompt_version_id"],
                final_prompt_hash=prompt_payload["final_prompt_hash"],
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return AIResponse(False, error_code="AI_RUNTIME_FAILED", error_message=str(exc), latency_ms=latency_ms)

    def health(self) -> dict[str, Any]:
        providers = self.db.scalars(select(LLMProvider).order_by(LLMProvider.priority.asc(), LLMProvider.id.asc())).all()
        health_items = []
        for provider in providers:
            adapter = RuntimeProviderAdapter(provider)
            health = adapter.health_check()
            provider.health_status = str(health.get("status", "UNKNOWN"))
            provider.last_health_check_at = utc_now()
            provider.last_health_error = None if provider.health_status == "HEALTHY" else str(health.get("message"))
            health_items.append(
                {
                    "provider_id": provider.id,
                    "provider_name": provider.provider_name,
                    "provider_type": provider.provider_type,
                    "status": provider.health_status,
                    "message": health.get("message"),
                    "api_key_configured": bool(provider.api_key),
                    "api_key_masked": mask_secret(provider.api_key),
                }
            )
        total_logs = self.db.scalar(select(func.count()).select_from(AIGenerationLog)) or 0
        fallback_logs = self.db.scalar(
            select(func.count()).select_from(AIGenerationLog).where(AIGenerationLog.fallback_used.is_(True))
        ) or 0
        error_logs = self.db.scalar(
            select(func.count()).select_from(AIGenerationLog).where(AIGenerationLog.status == "FAILED")
        ) or 0
        avg_latency = self.db.scalar(select(func.coalesce(func.avg(AIGenerationLog.latency_ms), 0))) or 0
        cost_today = self.db.scalar(select(func.coalesce(func.sum(AIGenerationLog.estimated_cost), 0))) or 0
        self.db.commit()
        return {
            "providers": health_items,
            "fallback_rate": round((fallback_logs / total_logs) * 100, 2) if total_logs else 0,
            "error_count": error_logs,
            "average_latency_ms": round(float(avg_latency), 2),
            "cost_today": round(float(cost_today), 6),
        }

    def _post(self, request: AIRequest) -> Post:
        if request.post_id is None:
            raise AIProviderError("post_id is required")
        post = self.db.get(Post, request.post_id)
        if not post:
            raise AIProviderError("post not found")
        return post

    def _log_embedding(self, request: AIRequest, post: Post, provider: LLMProvider | None, latency_ms: int, text: str) -> None:
        tokens = token_estimate(text)
        self.db.add(
            AIGenerationLog(
                post_id=post.id,
                ai_task_id=request.ai_task_id,
                provider_id=provider.id if provider else None,
                provider=provider.provider_name if provider else "Mock Provider",
                provider_type=provider.provider_type if provider else "mock",
                model=provider.model_name if provider else "mock-v0.3",
                model_name=provider.model_name if provider else "mock-v0.3",
                task_type=TASK_TYPE_EMBEDDING,
                prompt_version="embedding",
                purpose="EMBEDDING",
                duration_ms=latency_ms,
                latency_ms=latency_ms,
                token_estimate=tokens,
                input_tokens=tokens,
                output_tokens=1,
                total_tokens=tokens + 1,
                estimated_cost=0.0,
                provider_latency_ms=latency_ms,
                generation_source="MOCK" if provider is None else "LLM",
                fallback_used=provider is None,
                status="SUCCESS",
            )
        )
