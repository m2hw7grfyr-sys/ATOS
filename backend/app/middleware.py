import time
import uuid

from fastapi import Request


async def trace_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Process-Time-MS"] = f"{(time.perf_counter() - started) * 1000:.2f}"
    return response
