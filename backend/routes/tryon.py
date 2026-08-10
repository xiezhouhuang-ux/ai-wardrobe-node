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
