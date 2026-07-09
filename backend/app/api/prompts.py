from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PromptTemplate, PromptVersion
from app.response import ok
from app.schemas import PromptTemplateCreate, PromptVersionCreate
from app.serializers import serialize_model


router = APIRouter(tags=["prompts"])


def serialize_prompt_version(version: PromptVersion, db: Session) -> dict:
    item = serialize_model(version)
    template = db.get(PromptTemplate, version.prompt_template_id)
    item["template_name"] = template.name if template else None
    item["template_type"] = template.template_type if template else None
    return item


@router.get("/prompt-templates")
def list_prompt_templates(request: Request, db: Session = Depends(get_db)):
    templates = db.scalars(
        select(PromptTemplate).order_by(PromptTemplate.template_type.asc(), PromptTemplate.id.asc())
    ).all()
    return ok([serialize_model(template) for template in templates], request.state.trace_id)


@router.post("/prompt-templates")
def create_prompt_template(
    payload: PromptTemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    template = PromptTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return ok(serialize_model(template), request.state.trace_id, "prompt template created")


@router.get("/prompt-versions")
def list_prompt_versions(request: Request, db: Session = Depends(get_db)):
    versions = db.scalars(
        select(PromptVersion).order_by(PromptVersion.created_at.desc(), PromptVersion.id.desc())
    ).all()
    return ok([serialize_prompt_version(version, db) for version in versions], request.state.trace_id)


@router.post("/prompt-versions")
def create_prompt_version(
    payload: PromptVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    template = db.get(PromptTemplate, payload.prompt_template_id)
    if not template:
        raise HTTPException(status_code=404, detail="prompt template not found")
    if payload.is_default:
        existing = db.scalars(
            select(PromptVersion).where(PromptVersion.prompt_template_id == template.id)
        ).all()
        for version in existing:
            version.is_default = False
    version = PromptVersion(**payload.model_dump())
    db.add(version)
    db.commit()
    db.refresh(version)
    return ok(serialize_prompt_version(version, db), request.state.trace_id, "prompt version created")
