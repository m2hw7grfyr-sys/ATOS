from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlatformTemplateRule, ReplyTemplate
from app.response import ok
from app.serializers import serialize_model
from app.services.audit import write_audit
from app.services.reply_template_strategy import TemplateSelectionEngine, ensure_reply_template_seed


router = APIRouter(tags=["reply-templates"])


def serialize_template(template: ReplyTemplate, db: Session) -> dict:
    item = serialize_model(template)
    rules = db.scalars(
        select(PlatformTemplateRule)
        .where(PlatformTemplateRule.template_id == template.id)
        .order_by(PlatformTemplateRule.platform.asc())
    ).all()
    item["rules"] = [serialize_model(rule) for rule in rules]
    return item


@router.get("/reply-templates")
def list_reply_templates(request: Request, db: Session = Depends(get_db)):
    ensure_reply_template_seed(db)
    templates = db.scalars(select(ReplyTemplate).order_by(ReplyTemplate.id.asc())).all()
    db.commit()
    return ok([serialize_template(template, db) for template in templates], request.state.trace_id)


@router.get("/reply-templates/{template_id}")
def get_reply_template(template_id: int, request: Request, db: Session = Depends(get_db)):
    ensure_reply_template_seed(db)
    template = db.get(ReplyTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="reply template not found")
    return ok(serialize_template(template, db), request.state.trace_id)


@router.put("/reply-templates/{template_id}")
def update_reply_template(template_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    template = db.get(ReplyTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="reply template not found")
    for key in ["description", "risk_level", "enabled"]:
        if key in payload:
            setattr(template, key, payload[key])
    write_audit(
        db,
        action="Template Updated",
        entity_type="ReplyTemplate",
        entity_uuid=template.uuid,
        actor="administrator",
        trace_id=request.state.trace_id,
        detail={"template_id": template.id, "payload": {key: payload.get(key) for key in ["description", "risk_level", "enabled"]}},
    )
    db.commit()
    db.refresh(template)
    return ok(serialize_template(template, db), request.state.trace_id, "reply template updated")


@router.get("/platform-template-rules")
def list_platform_template_rules(request: Request, db: Session = Depends(get_db)):
    ensure_reply_template_seed(db)
    rules = db.scalars(select(PlatformTemplateRule).order_by(PlatformTemplateRule.platform.asc(), PlatformTemplateRule.id.asc())).all()
    result = []
    for rule in rules:
        item = serialize_model(rule)
        template = db.get(ReplyTemplate, rule.template_id)
        item["template_name_cn"] = template.name_cn if template else None
        item["funnel_intent"] = template.funnel_intent if template else None
        item["cta_strength"] = template.cta_strength if template else None
        result.append(item)
    db.commit()
    return ok(result, request.state.trace_id)


@router.put("/platform-template-rules/{rule_id}")
def update_platform_template_rule(rule_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    rule = db.get(PlatformTemplateRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="platform template rule not found")
    for key in ["allowed", "default_enabled", "max_daily_ratio", "risk_level", "allow_auto_assisted", "notes"]:
        if key in payload:
            setattr(rule, key, payload[key])
    write_audit(
        db,
        action="Template Rule Updated",
        entity_type="PlatformTemplateRule",
        entity_uuid=rule.uuid,
        actor="administrator",
        trace_id=request.state.trace_id,
        detail={"rule_id": rule.id, "platform": rule.platform, "template_id": rule.template_id},
    )
    db.commit()
    db.refresh(rule)
    return ok(serialize_model(rule), request.state.trace_id, "platform template rule updated")


@router.get("/template-performance")
def get_template_performance(request: Request, db: Session = Depends(get_db)):
    ensure_reply_template_seed(db)
    return ok(TemplateSelectionEngine(db).performance(), request.state.trace_id)
