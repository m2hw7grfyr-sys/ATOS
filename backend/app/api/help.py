from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.response import ok
from app.services.manuals import MANUALS, can_view_manual, ensure_manual_pdf, get_manual_payload, list_manuals, normalize_role


router = APIRouter(prefix="/help", tags=["help"])


@router.get("/manuals")
def manuals(request: Request, role: str = Query("Operator")):
    return ok(
        {
            "role": normalize_role(role),
            "manuals": list_manuals(role),
            "topics": [
                "操作人员手册",
                "Reddit 操作说明",
                "X 操作说明",
                "SEMI_AUTO 使用说明",
                "AUTO_ASSISTED 使用说明",
                "Reply Templates 五类中文模板说明",
                "Waiting Manual 处理",
                "Mark Failed / Retry / Cancel",
                "Emergency Stop 使用说明",
                "常见问题",
            ],
        },
        request.state.trace_id,
    )


@router.get("/manuals/{manual_key}")
def manual_detail(manual_key: str, request: Request, role: str = Query("Operator")):
    if manual_key not in MANUALS:
        raise HTTPException(status_code=404, detail="manual not found")
    manual = MANUALS[manual_key]
    if not can_view_manual(manual, role):
        raise HTTPException(status_code=403, detail="administrator manual requires Administrator role")
    return ok(get_manual_payload(manual_key, role), request.state.trace_id)


@router.get("/manuals/{manual_key}/pdf")
def manual_pdf(manual_key: str, role: str = Query("Operator")):
    if manual_key not in MANUALS:
        raise HTTPException(status_code=404, detail="manual not found")
    manual = MANUALS[manual_key]
    if not can_view_manual(manual, role):
        raise HTTPException(status_code=403, detail="administrator manual requires Administrator role")
    pdf_path = ensure_manual_pdf(manual_key)
    return FileResponse(pdf_path, media_type="application/pdf", filename=manual.pdf_name)

