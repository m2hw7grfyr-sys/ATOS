from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlatformRegistry
from app.response import ok
from app.serializers import serialize_model
from app.services.platform_runtime import PlatformRuntime


router = APIRouter(prefix="/platform-runtime", tags=["platform-runtime"])


def serialize_registry(item: PlatformRegistry) -> dict:
    data = serialize_model(item)
    capabilities = item.capabilities or {}
    if isinstance(capabilities, dict):
        data["capability_list"] = sorted([key for key, enabled in capabilities.items() if enabled])
    elif isinstance(capabilities, list):
        data["capability_list"] = sorted([str(key) for key in capabilities])
    else:
        data["capability_list"] = []
    return data


@router.get("")
def runtime_overview(request: Request, db: Session = Depends(get_db)):
    runtime = PlatformRuntime(db)
    registries = runtime.ensure_registry()
    db.commit()
    return ok(
        {
            "discovered": runtime.discover(),
            "registry": [serialize_registry(item) for item in registries],
            "statistics": runtime.statistics(),
        },
        request.state.trace_id,
    )


@router.get("/platforms")
def list_platform_registry(request: Request, db: Session = Depends(get_db)):
    runtime = PlatformRuntime(db)
    items = runtime.ensure_registry()
    db.commit()
    return ok([serialize_registry(item) for item in items], request.state.trace_id)


@router.get("/health")
def platform_health(request: Request, db: Session = Depends(get_db)):
    rows = PlatformRuntime(db).health()
    db.commit()
    return ok(
        [{"platform": row["registry"].platform_name, **serialize_registry(row["registry"]), "health": row["health"]} for row in rows],
        request.state.trace_id,
    )


@router.post("/capability-check")
def capability_check(payload: dict, request: Request, db: Session = Depends(get_db)):
    platform = str(payload.get("platform") or "")
    action_type = payload.get("action_type")
    if not platform:
        raise HTTPException(status_code=400, detail="platform is required")
    result = PlatformRuntime(db).check_capability(platform, action_type)
    return ok(result, request.state.trace_id)


@router.put("/platforms/{registry_id}")
def update_platform_registry(registry_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    item = db.get(PlatformRegistry, registry_id)
    if not item:
        raise HTTPException(status_code=404, detail="platform registry item not found")
    for key in ["enabled", "version", "capabilities", "status"]:
        if key in payload:
            setattr(item, key, payload[key])
    db.commit()
    db.refresh(item)
    return ok(serialize_registry(item), request.state.trace_id, "platform registry updated")


@router.get("/statistics")
def platform_statistics(request: Request, db: Session = Depends(get_db)):
    return ok(PlatformRuntime(db).statistics(), request.state.trace_id)
