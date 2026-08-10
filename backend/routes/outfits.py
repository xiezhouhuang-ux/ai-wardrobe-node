"""搭配/日历接口：保存与查询。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.deps import require_openid
import store

router = APIRouter(tags=["outfits"])


class OutfitPayload(BaseModel):
    date: str = ""
    items: list = []
    note: str = ""


@router.post("/api/outfits")
def api_save_outfit(payload: OutfitPayload, openid: str = Depends(require_openid)):
    if not payload.date:
        raise HTTPException(status_code=400, detail="缺少 date")
    store.save_outfit({
        "openid": openid,
        "date": payload.date,
        "items": payload.items,
        "note": payload.note,
    })
    return {"ok": True}


@router.get("/api/outfits")
def api_get_outfits(openid: str = Depends(require_openid)):
    return store.get_outfits(openid)
