"""内容安全预检接口：供前端显式调用（如上传前预检）。"""
from fastapi import APIRouter, Body, HTTPException

import security as sec

router = APIRouter(tags=["security"])


@router.post("/api/security/check")
def api_security_check(body: dict = Body(default={})):
    text = body.get("text", "") or ""
    images = body.get("images", []) or []
    try:
        sec.check_text(text or "", scene=2)
        for url in images:
            sec.check_image(url)
        return {"ok": True, "passed": True}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=f"内容未通过安全检测: {pe}")
