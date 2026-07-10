from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LLMProvider, Platform, PlatformWeight, ProviderRouting, SystemSetting
from app.response import ok
from app.schemas import (
    LLMProviderCreate,
    LLMProviderUpdate,
    PlatformWeightUpdate,
    PlaywrightSettingsUpdate,
    ProviderRoutingCreate,
    ProviderRoutingUpdate,
    SchedulerSettingsUpdate,
    SettingUpdate,
    TgeSettingsUpdate,
)
from app.serializers import serialize_model
from app.services.ai import mask_secret, test_provider_config
from app.services.scheduler import (
    ensure_platform_weights,
    get_scheduler_settings,
    save_scheduler_settings,
)
from app.services.tge import get_tge_settings, safe_tge_settings, save_tge_settings
from app.services.playwright_runner import get_playwright_settings, save_playwright_settings


router = APIRouter(prefix="/settings", tags=["settings"])


ALLOWED_PROVIDER_TYPES = {"openai", "anthropic", "gemini", "ollama", "custom", "custom_http", "mock"}
ALLOWED_TASK_TYPES = {
    "ANALYSIS",
    "REPLY",
    "REPLY_GENERATION",
    "REWRITE",
    "EMBEDDING",
    "CLASSIFICATION",
    "SUMMARY",
}


def serialize_llm_provider(provider: LLMProvider) -> dict:
    item = serialize_model(provider)
    item["api_key"] = None
    item["api_key_configured"] = bool(provider.api_key)
    item["api_key_masked"] = mask_secret(provider.api_key)
    return item


def serialize_provider_routing(route: ProviderRouting, db: Session) -> dict:
    item = serialize_model(route)
    preferred = db.get(LLMProvider, route.preferred_provider_id) if route.preferred_provider_id else None
    fallback = db.get(LLMProvider, route.fallback_provider_id) if route.fallback_provider_id else None
    item["preferred_provider"] = preferred.provider_name if preferred else None
    item["fallback_provider"] = fallback.provider_name if fallback else None
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


@router.get("/playwright")
def get_playwright_config(request: Request, db: Session = Depends(get_db)):
    return ok(get_playwright_settings(db), request.state.trace_id)


@router.put("/playwright")
def update_playwright_config(
    payload: PlaywrightSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    return ok(save_playwright_settings(db, payload.model_dump()), request.state.trace_id, "Playwright settings updated")


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


@router.post("/llm-providers/{provider_id}/test")
def test_llm_provider(provider_id: int, request: Request, db: Session = Depends(get_db)):
    provider = db.get(LLMProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")
    return ok(test_provider_config(db, provider), request.state.trace_id, "LLM provider tested")


@router.get("/provider-routing")
def list_provider_routing(request: Request, db: Session = Depends(get_db)):
    routes = db.scalars(
        select(ProviderRouting).order_by(ProviderRouting.priority.asc(), ProviderRouting.id.asc())
    ).all()
    return ok([serialize_provider_routing(route, db) for route in routes], request.state.trace_id)


@router.post("/provider-routing")
def create_provider_routing(
    payload: ProviderRoutingCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    task_type = payload.task_type.upper()
    if task_type not in ALLOWED_TASK_TYPES:
        raise HTTPException(status_code=422, detail="unsupported task_type")
    route = ProviderRouting(
        name=payload.name,
        platform=payload.platform,
        task_type=task_type,
        strategy=payload.strategy,
        min_commercial_score=payload.min_commercial_score,
        max_risk_score=payload.max_risk_score,
        preferred_provider_id=payload.preferred_provider_id,
        fallback_provider_id=payload.fallback_provider_id,
        enabled=payload.enabled,
        priority=payload.priority,
        remark=payload.remark,
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return ok(serialize_provider_routing(route, db), request.state.trace_id, "provider route created")


@router.put("/provider-routing/{route_id}")
def update_provider_routing(
    route_id: int,
    payload: ProviderRoutingUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    route = db.get(ProviderRouting, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="provider route not found")
    updates = payload.model_dump(exclude_unset=True)
    if "task_type" in updates and updates["task_type"]:
        updates["task_type"] = str(updates["task_type"]).upper()
        if updates["task_type"] not in ALLOWED_TASK_TYPES:
            raise HTTPException(status_code=422, detail="unsupported task_type")
    for key, value in updates.items():
        setattr(route, key, value)
    db.commit()
    db.refresh(route)
    return ok(serialize_provider_routing(route, db), request.state.trace_id, "provider route updated")


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
