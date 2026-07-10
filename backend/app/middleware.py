import time
import uuid
import logging

from fastapi import Request


logger = logging.getLogger("atos.request")


async def trace_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "trace_id": trace_id,
            "request_id": request_id,
            "atos_module": "http",
            "action": request.url.path,
            "duration": duration_ms,
            "result": response.status_code,
        },
    )
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-MS"] = f"{duration_ms:.2f}"
    return response
