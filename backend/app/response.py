from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    success: bool = True
    code: str = "OK"
    message: str = "success"
    data: Any = None
    trace_id: str


def ok(data: Any, trace_id: str, message: str = "success") -> dict[str, Any]:
    return {
        "success": True,
        "code": "OK",
        "message": message,
        "data": data,
        "trace_id": trace_id,
    }
