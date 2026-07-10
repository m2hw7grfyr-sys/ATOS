from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException


def error_payload(
    request: Request,
    code: str,
    message: str,
    data=None,
) -> dict:
    return {
        "success": False,
        "code": code,
        "message": message,
        "trace_id": getattr(request.state, "trace_id", "unavailable"),
        "data": data,
    }


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(request, f"HTTP-{exc.status_code}", str(exc.detail)),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            request,
            "SYS-0001",
            "validation error",
            exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_payload(request, "SYS-9999", "internal server error"),
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_payload(request, "DB-0001", "database error"),
    )
