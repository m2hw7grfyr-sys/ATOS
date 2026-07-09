from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models import CrawlLog, DataSource, Platform
from app.response import ok
from app.schemas import DataSourceCreate, DataSourceUpdate
from app.serializers import serialize_model
from app.services.apify import ApifyService, ApifyServiceError


router = APIRouter(prefix="/data-sources", tags=["data-sources"])


def _masked_token(token: str) -> str:
    if not token:
        return ""
    if len(token) < 8:
        return "********"
    return f"{token[:4]}...{token[-4:]}"


def _serialize_source(
    item: DataSource,
    db: Session,
    latest_log: CrawlLog | None = None,
) -> dict[str, Any]:
    result = serialize_model(item)
    config = dict(item.config or {})
    token = str(config.pop("apify_token", "") or get_settings().apify_token)
    config["token_configured"] = bool(token)
    config["token_masked"] = _masked_token(token)
    result["config"] = config
    platform = db.get(Platform, item.platform_id) if item.platform_id else None
    result["platform"] = platform.slug if platform else config.get("platform")
    if latest_log is None:
        latest_log = db.scalar(
            select(CrawlLog)
            .where(CrawlLog.data_source_id == item.id)
            .order_by(CrawlLog.started_at.desc())
            .limit(1)
        )
    result["latest_log"] = serialize_model(latest_log) if latest_log else None
    return result


def _merge_config(
    incoming: dict[str, Any],
    token: str | None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = dict(existing or {})
    submitted = dict(incoming)
    nested_token = submitted.pop("apify_token", None)
    config.update(submitted)
    new_token = token or nested_token
    if new_token:
        config["apify_token"] = new_token
    return config


def _get_source(source_id: int, db: Session) -> DataSource:
    item = db.get(DataSource, source_id)
    if item is None:
        raise HTTPException(status_code=404, detail="data source not found")
    return item


@router.get("")
def list_data_sources(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(DataSource).order_by(DataSource.created_at.desc())).all()
    return ok(
        [_serialize_source(item, db) for item in items],
        request.state.trace_id,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_data_source(
    payload: DataSourceCreate, request: Request, db: Session = Depends(get_db)
):
    values = payload.model_dump(exclude={"apify_token"})
    values["config"] = _merge_config(payload.config, payload.apify_token)
    item = DataSource(**values)
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(
        _serialize_source(item, db),
        request.state.trace_id,
        "data source created",
    )


@router.get("/platforms")
def list_source_platforms(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Platform).order_by(Platform.name)).all()
    return ok(
        [
            {
                "id": item.id,
                "name": item.name,
                "slug": item.slug,
                "enabled": item.enabled,
            }
            for item in items
        ],
        request.state.trace_id,
    )


@router.put("/{source_id}")
def update_data_source(
    source_id: int,
    payload: DataSourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    item = _get_source(source_id, db)
    values = payload.model_dump(exclude_unset=True, exclude={"apify_token", "config"})
    for key, value in values.items():
        setattr(item, key, value)
    if payload.config is not None or payload.apify_token:
        item.config = _merge_config(
            payload.config or {},
            payload.apify_token,
            item.config,
        )
    db.commit()
    db.refresh(item)
    return ok(
        _serialize_source(item, db),
        request.state.trace_id,
        "data source updated",
    )


@router.post("/{source_id}/test")
def test_data_source(
    source_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    item = _get_source(source_id, db)
    try:
        result = ApifyService(db).test_connection(item)
        item.status = "ACTIVE"
        config = dict(item.config or {})
        config["last_error"] = ""
        item.config = config
        db.commit()
        return ok(result, request.state.trace_id, "Apify connection succeeded")
    except ApifyServiceError as exc:
        item.status = "ERROR"
        config = dict(item.config or {})
        config["last_error"] = str(exc)[:500]
        item.config = config
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{source_id}/run")
def run_data_source(
    source_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    item = _get_source(source_id, db)
    log = ApifyService(db).run(item)
    return ok(
        serialize_model(log),
        request.state.trace_id,
        "crawl completed" if log.status == "SUCCEEDED" else "crawl failed",
    )


@router.get("/{source_id}/logs")
def list_crawl_logs(
    source_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _get_source(source_id, db)
    logs = db.scalars(
        select(CrawlLog)
        .where(CrawlLog.data_source_id == source_id)
        .order_by(CrawlLog.started_at.desc())
        .limit(100)
    ).all()
    return ok(
        [serialize_model(item) for item in logs],
        request.state.trace_id,
    )
