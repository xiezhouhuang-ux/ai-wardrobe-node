"""试穿记录接口：保存试穿结果、查询记录列表。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.deps import require_openid
from services import wardrobe as wardrobe_svc
import store

router = APIRouter(tags=["tryon"])


class SaveTryonPayload(BaseModel):
    itemIds: list = []
    resultUrl: str = ""


@router.post("/api/tryon/save")
def api_save_tryon(payload: SaveTryonPayload, openid: str = Depends(require_openid)):
    try:
        return wardrobe_svc.save_tryon(openid, payload.itemIds, payload.resultUrl)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/tryon/records")
def api_tryon_records(openid: str = Depends(require_openid)):
    return store.get_tryon_records(openid)


@router.get("/api/tryon/records/{record_id}")
def api_tryon_record_detail(record_id: str, openid: str = Depends(require_openid)):
    record = store.get_tryon_record(record_id, openid)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.delete("/api/tryon/records/{record_id}")
def api_delete_tryon_record(record_id: str, openid: str = Depends(require_openid)):
    ok = store.delete_tryon_record(record_id, openid)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权删除")
    return {"ok": True}
