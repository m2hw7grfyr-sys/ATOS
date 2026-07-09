from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from app.api import (
    accounts,
    ai,
    dashboard,
    data_sources,
    health,
    posts,
    scheduler,
    settings,
    statistics,
)
from app.config import get_settings
from app.exception_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.middleware import trace_middleware


settings_config = get_settings()
app = FastAPI(
    title=settings_config.app_name,
    version=settings_config.app_version,
    description="ATOS v0.4 local application API",
)
app.middleware("http")(trace_middleware)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_config.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(data_sources.router)
app.include_router(posts.router)
app.include_router(ai.router)
app.include_router(scheduler.router)
app.include_router(accounts.router)
app.include_router(settings.router)
app.include_router(statistics.router)
