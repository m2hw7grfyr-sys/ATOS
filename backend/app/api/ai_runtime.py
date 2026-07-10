from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIGenerationLog, LLMProvider
from app.response import ok
from app.schemas import LLMProviderCreate, LLMProviderUpdate
from app.serializers import serialize_model
from app.services.ai import mask_secret, test_provider_config
from app.services.ai_runtime import (
    AIRequest,
    AIRuntime,
    PromptContext,
    TASK_TYPE_ANALYSIS,
    TASK_TYPE_EMBEDDING,
)


router = APIRouter(prefix="/ai-runtime", tags=["ai-runtime"])


ALLOWED_PROVIDER_TYPES = {"mock", "openai", "anthropic", "gemini", "ollama", "custom", "custom_http"}


def serialize_llm_provider(provider: LLMProvider) -> dict[str, Any]:
    item = serialize_model(provider)
    item["api_key"] = None
    item["api_key_configured"] = bool(provider.api_key)
    item["api_key_masked"] = mask_secret(provider.api_key)
    return item


def serialize_generation_log(log: AIGenerationLog) -> dict[str, Any]:
    item = serialize_model(log)
    item["prompt"] = None
    return item


@router.get("/providers")
def list_runtime_providers(request: Request, db: Session = Depends(get_db)):
    providers = db.scalars(
        select(LLMProvider).order_by(LLMProvider.priority.asc(), LLMProvider.id.asc())
    ).all()
    return ok([serialize_llm_provider(provider) for provider in providers], request.state.trace_id)


@router.post("/providers")
def create_runtime_provider(payload: LLMProviderCreate, request: Request, db: Session = Depends(get_db)):
    provider_type = payload.provider_type.lower()
    if provider_type not in ALLOWED_PROVIDER_TYPES:
        raise HTTPException(status_code=422, detail="unsupported provider_type")
    provider = LLMProvider(
        provider_name=payload.provider_name,
        provider_type=provider_type,
        api_base_url=payload.api_base_url,
        api_key=payload.api_key,
        model_name=payload.model_name,
        enabled=payload.enabled,
        priority=payload.priority,
        use_for_analysis=payload.use_for_analysis,
        use_for_reply=payload.use_for_reply,
        use_for_embedding=payload.use_for_embedding,
        is_mock=payload.is_mock or provider_type == "mock",
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        remark=payload.remark,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return ok(serialize_llm_provider(provider), request.state.trace_id, "AI Runtime provider created")


@router.put("/providers/{provider_id}")
def update_runtime_provider(
    provider_id: int,
    payload: LLMProviderUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    provider = db.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    updates = payload.model_dump(exclude_unset=True)
    if "provider_type" in updates:
        updates["provider_type"] = str(updates["provider_type"]).lower()
        if updates["provider_type"] not in ALLOWED_PROVIDER_TYPES:
            raise HTTPException(status_code=422, detail="unsupported provider_type")
    if updates.get("api_key") == "":
        updates.pop("api_key")
    for key, value in updates.items():
        setattr(provider, key, value)
    if provider.provider_type == "mock":
        provider.is_mock = True
    db.commit()
    db.refresh(provider)
    return ok(serialize_llm_provider(provider), request.state.trace_id, "AI Runtime provider updated")


@router.post("/providers/{provider_id}/test")
def test_runtime_provider(provider_id: int, request: Request, db: Session = Depends(get_db)):
    provider = db.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    return ok(test_provider_config(db, provider), request.state.trace_id, "AI Runtime provider tested")


@router.get("/health")
def get_runtime_health(request: Request, db: Session = Depends(get_db)):
    return ok(AIRuntime(db).health(), request.state.trace_id)


@router.get("/logs")
def list_runtime_logs(request: Request, db: Session = Depends(get_db), limit: int = 50):
    limit = min(max(limit, 1), 200)
    logs = db.scalars(
        select(AIGenerationLog).order_by(AIGenerationLog.created_at.desc(), AIGenerationLog.id.desc()).limit(limit)
    ).all()
    return ok([serialize_generation_log(log) for log in logs], request.state.trace_id)


def _request_from_payload(payload: dict[str, Any], trace_id: str, default_task_type: str) -> AIRequest:
    prompt_context = payload.get("prompt_context") or {}
    if not isinstance(prompt_context, dict):
        prompt_context = {}
    return AIRequest(
        request_id=str(payload.get("request_id") or trace_id),
        task_type=str(payload.get("task_type") or default_task_type).upper(),
        post_id=payload.get("post_id"),
        platform=payload.get("platform"),
        strategy=payload.get("strategy"),
        prompt_context=PromptContext(
            strategy=prompt_context.get("strategy") or payload.get("strategy"),
            tone=prompt_context.get("tone"),
            variables=prompt_context.get("variables") or {},
            history_context=prompt_context.get("history_context"),
            role_prompt=prompt_context.get("role_prompt"),
        ),
        preferred_provider=payload.get("preferred_provider"),
        fallback_enabled=bool(payload.get("fallback_enabled", True)),
        metadata=payload.get("metadata") or {},
        ai_task_id=payload.get("ai_task_id"),
    )


@router.post("/generate")
def runtime_generate(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    ai_request = _request_from_payload(payload, request.state.trace_id, TASK_TYPE_ANALYSIS)
    response = AIRuntime(db).generate(ai_request)
    db.commit()
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error_message or "AI Runtime generation failed")
    return ok(response.as_dict(), request.state.trace_id, "AI Runtime generation completed")


@router.post("/embed")
def runtime_embed(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    ai_request = _request_from_payload(payload, request.state.trace_id, TASK_TYPE_EMBEDDING)
    ai_request.task_type = TASK_TYPE_EMBEDDING
    response = AIRuntime(db).generate_embedding(ai_request)
    db.commit()
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error_message or "AI Runtime embedding failed")
    return ok(response.as_dict(), request.state.trace_id, "AI Runtime embedding completed")
