from fastapi import APIRouter, Request

from app.config import get_settings
from app.response import ok


router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    settings = get_settings()
    return ok(
        {
            "status": "HEALTHY",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        },
        request.state.trace_id,
    )
