from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.base import PlatformAdapter, ScaffoldAdapter
from app.adapters.facebook import FacebookAdapter
from app.adapters.instagram import InstagramAdapter
from app.adapters.reddit import RedditAdapter
from app.adapters.tiktok import TikTokAdapter
from app.adapters.x import XAdapter
from app.models import ExecutionTask, PlatformRegistry, StatisticSnapshot, utc_now


CAPABILITY_BY_ACTION = {
    "PREPARE_REPLY": "REPLY",
    "REPLY": "REPLY",
    "OPEN_PAGE": "BROWSE",
    "BROWSE_POST": "BROWSE",
    "MIXED_ENGAGEMENT": "BROWSE",
    "LIKE_POST": "LIKE",
    "VISIT_PROFILE": "PROFILE_VISIT",
}


class PlatformCapabilityError(ValueError):
    pass


class PlatformRuntime:
    def __init__(self, db: Session, mock_mode: bool = True):
        self.db = db
        self.mock_mode = mock_mode
        self.adapter_classes = {
            "reddit": RedditAdapter,
            "x": XAdapter,
            "facebook": FacebookAdapter,
            "instagram": InstagramAdapter,
            "tiktok": TikTokAdapter,
        }

    def discover(self) -> list[dict[str, Any]]:
        return [
            {
                "platform_name": key,
                "adapter_name": cls.adapter_name,
                "version": cls.version,
                "capabilities": sorted(cls.capabilities),
            }
            for key, cls in sorted(self.adapter_classes.items())
        ]

    def ensure_registry(self) -> list[PlatformRegistry]:
        items: list[PlatformRegistry] = []
        for key, cls in self.adapter_classes.items():
            item = self.db.scalar(select(PlatformRegistry).where(PlatformRegistry.platform_name == key))
            if not item:
                item = PlatformRegistry(
                    platform_name=key,
                    adapter_name=cls.adapter_name,
                    version=cls.version,
                    capabilities={capability: True for capability in sorted(cls.capabilities)},
                    enabled=True,
                    status="UNKNOWN",
                )
                self.db.add(item)
                self.db.flush()
            items.append(item)
        return items

    def adapter_for(self, platform: str) -> PlatformAdapter:
        platform_key = (platform or "").lower()
        registry = self.db.scalar(select(PlatformRegistry).where(PlatformRegistry.platform_name == platform_key))
        if registry and not registry.enabled:
            raise PlatformCapabilityError(f"platform disabled: {platform_key}")
        adapter_class = self.adapter_classes.get(platform_key)
        if not adapter_class:
            adapter = ScaffoldAdapter(self.db, mock_mode=self.mock_mode)
            adapter.platform = platform_key or "unknown"
            adapter.adapter_name = "ScaffoldAdapter"
            return adapter
        return adapter_class(self.db, mock_mode=self.mock_mode)

    def required_capability(self, action_type: str | None) -> str:
        return CAPABILITY_BY_ACTION.get((action_type or "").upper(), (action_type or "BROWSE").upper())

    def check_capability(self, platform: str, action_type: str | None) -> dict[str, Any]:
        adapter = self.adapter_for(platform)
        required = self.required_capability(action_type)
        supported = required in adapter.capabilities
        if not supported:
            return {
                "supported": False,
                "platform": adapter.platform,
                "action_type": action_type,
                "capability_required": required,
                "capabilities": sorted(adapter.capabilities),
                "reason": f"{adapter.platform} does not support {required}",
            }
        return {
            "supported": True,
            "platform": adapter.platform,
            "action_type": action_type,
            "capability_required": required,
            "capabilities": sorted(adapter.capabilities),
        }

    def assert_capability(self, platform: str, action_type: str | None) -> dict[str, Any]:
        result = self.check_capability(platform, action_type)
        if not result["supported"]:
            raise PlatformCapabilityError(result["reason"])
        return result

    def health(self) -> list[dict[str, Any]]:
        rows = []
        for registry in self.ensure_registry():
            try:
                adapter = self.adapter_for(registry.platform_name)
                health = adapter.health_check()
                registry.status = str(health.get("status", "HEALTHY"))
                registry.version = adapter.version
                registry.adapter_name = adapter.adapter_name
                registry.capabilities = {capability: True for capability in sorted(adapter.capabilities)}
                registry.last_error = None
            except Exception as exc:
                registry.status = "ERROR"
                registry.last_error = str(exc)
                registry.error_count += 1
                health = {"status": "ERROR", "message": str(exc)}
            registry.last_health_check_at = utc_now()
            rows.append({"registry": registry, "health": health})
        self.db.flush()
        return rows

    def statistics(self) -> dict[str, Any]:
        tasks = self.db.scalars(select(ExecutionTask)).all()
        by_platform: dict[str, dict[str, Any]] = {}
        for task in tasks:
            key = task.platform or "unknown"
            item = by_platform.setdefault(key, {"platform": key, "tasks": 0, "success": 0, "failed": 0})
            item["tasks"] += 1
            if task.status == "SUCCESS":
                item["success"] += 1
            if task.status == "FAILED":
                item["failed"] += 1
        for item in by_platform.values():
            total = max(item["tasks"], 1)
            item["success_rate"] = round((item["success"] / total) * 100, 2)
            item["failure_rate"] = round((item["failed"] / total) * 100, 2)
        snapshot_total = self.db.scalar(
            select(func.coalesce(func.sum(StatisticSnapshot.value), 0)).where(
                StatisticSnapshot.metric == "platform_tasks"
            )
        ) or 0
        return {"tasks_by_platform": list(by_platform.values()), "snapshot_total": snapshot_total}
