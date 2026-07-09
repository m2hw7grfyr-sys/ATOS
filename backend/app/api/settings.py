from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LLMProvider, Platform, PlatformWeight, SystemSetting
from app.response import ok
from app.schemas import (
    LLMProviderCreate,
    LLMProviderUpdate,
    PlatformWeightUpdate,
    SchedulerSettingsUpdate,
    SettingUpdate,
    TgeSettingsUpdate,
)
from app.serializers import serialize_model
from app.services.ai import mask_secret
from app.services.scheduler import (
    ensure_platform_weights,
    get_scheduler_settings,
    save_scheduler_settings,
)
from app.services.tge import get_tge_settings, safe_tge_settings, save_tge_settings


router = APIRouter(prefix="/settings", tags=["settings"])


ALLOWED_PROVIDER_TYPES = {"openai", "anthropic", "gemini", "ollama", "custom", "mock"}


def serialize_llm_provider(provider: LLMProvider) -> dict:
    item = serialize_model(provider)
    item["api_key"] = None
    item["api_key_configured"] = bool(provider.api_key)
    item["api_key_masked"] = mask_secret(provider.api_key)
    return item


@router.get("")
def list_settings(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)).all()
    safe_items = []
    for item in items:
        serialized = serialize_model(item)
        if item.is_secret:
            serialized["value"] = {"configured": bool(item.value)}
        safe_items.append(serialized)
    return ok(safe_items, request.state.trace_id)


@router.get("/scheduler")
def get_scheduler_config(request: Request, db: Session = Depends(get_db)):
    return ok(get_scheduler_settings(db), request.state.trace_id)


@router.put("/scheduler")
def update_scheduler_config(
    payload: SchedulerSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    values = save_scheduler_settings(db, payload.model_dump())
    return ok(values, request.state.trace_id, "scheduler settings updated")


def serialize_platform_weight(item: PlatformWeight, db: Session) -> dict:
    result = serialize_model(item)
    platform = db.get(Platform, item.platform_id)
    result["platform"] = platform.slug if platform else None
    result["platform_name"] = platform.name if platform else None
    return result


@router.get("/platform-weights")
def list_platform_weights(request: Request, db: Session = Depends(get_db)):
    weights = ensure_platform_weights(db)
    db.commit()
    return ok([serialize_platform_weight(item, db) for item in weights], request.state.trace_id)


@router.put("/platform-weights")
def update_platform_weights(
    payload: PlatformWeightUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    ensure_platform_weights(db)
    for raw in payload.weights:
        platform_slug = raw.get("platform")
        platform_id = raw.get("platform_id")
        platform = None
        if platform_id:
            platform = db.get(Platform, int(platform_id))
        elif platform_slug:
            platform = db.scalar(select(Platform).where(Platform.slug == platform_slug))
        if not platform:
            continue
        item = db.scalar(select(PlatformWeight).where(PlatformWeight.platform_id == platform.id))
        if not item:
            item = PlatformWeight(platform_id=platform.id)
            db.add(item)
        item.weight = int(raw.get("weight", item.weight))
        item.enabled = bool(raw.get("enabled", item.enabled))
        item.remark = raw.get("remark", item.remark)
    db.commit()
    weights = ensure_platform_weights(db)
    db.commit()
    return ok([serialize_platform_weight(item, db) for item in weights], request.state.trace_id, "platform weights updated")


@router.get("/tge")
def get_tge_config(request: Request, db: Session = Depends(get_db)):
    return ok(safe_tge_settings(get_tge_settings(db)), request.state.trace_id)


@router.put("/tge")
def update_tge_config(
    payload: TgeSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    return ok(save_tge_settings(db, payload.model_dump()), request.state.trace_id, "TGE settings updated")


@router.get("/llm-providers")
def list_llm_providers(request: Request, db: Session = Depends(get_db)):
    providers = db.scalars(
        select(LLMProvider).order_by(LLMProvider.priority.asc(), LLMProvider.id.asc())
    ).all()
    return ok([serialize_llm_provider(provider) for provider in providers], request.state.trace_id)


@router.post("/llm-providers")
def create_llm_provider(
    payload: LLMProviderCreate,
    request: Request,
    db: Session = Depends(get_db),
):
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
    return ok(serialize_llm_provider(provider), request.state.trace_id, "LLM provider created")


@router.put("/llm-providers/{provider_id}")
def update_llm_provider(
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
    return ok(serialize_llm_provider(provider), request.state.trace_id, "LLM provider updated")


@router.put("/{key}")
def update_setting(
    key: str,
    payload: SettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not item:
        raise HTTPException(status_code=404, detail="setting not found")
    item.value = payload.value
    db.commit()
    db.refresh(item)
    return ok(serialize_model(item), request.state.trace_id, "setting updated")
