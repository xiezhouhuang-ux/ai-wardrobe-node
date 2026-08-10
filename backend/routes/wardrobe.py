"""衣橱核心接口：识别、分割预览、入库、AI 试穿。"""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

from core.deps import require_openid
from services import wardrobe as wardrobe_svc
import store

router = APIRouter(tags=["wardrobe"])


@router.get("/api/items")
def api_list_items(openid: str = Depends(require_openid)):
    """小程序端：列出当前用户的衣橱单品（复用旧版格式：直接返回数组）。"""
    return store.get_items(openid)


@router.get("/api/items/{item_id}")
def api_get_item(item_id: str, openid: str = Depends(require_openid)):
    """小程序端：获取单个单品详情。"""
    item = store.get_item(item_id, openid)
    if not item:
        raise HTTPException(status_code=404, detail="单品不存在")
    return item


@router.delete("/api/items/{item_id}")
def api_delete_item(item_id: str, openid: str = Depends(require_openid)):
    """小程序端：删除当前用户的某个单品。"""
    if not store.delete_item(item_id, openid):
        raise HTTPException(status_code=404, detail="单品不存在")
    return {"ok": True}


@router.get("/api/stats")
def api_stats(openid: str = Depends(require_openid)):
    """小程序端：衣橱统计（复用旧版格式：{total, byCategory}）。"""
    return store.get_stats(openid)


@router.post("/api/process")
async def api_process(request: Request, openid: str = Depends(require_openid)):
    form = await request.form()
    files = form.getlist("photos") if hasattr(form, "getlist") else (form.get("photos") or [])
    try:
        return wardrobe_svc.process_photo(openid, files)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/analyze")
async def api_analyze(request: Request, openid: str = Depends(require_openid)):
    form = await request.form()
    files = form.getlist("photos") if hasattr(form, "getlist") else (form.get("photos") or [])
    try:
        return wardrobe_svc.analyze(openid, files)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/commit")
def api_commit(payload: dict = Body(default={}), openid: str = Depends(require_openid)):
    items = payload.get("items", []) or []
    try:
        return wardrobe_svc.commit(openid, items)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


class TryonPayload(BaseModel):
    itemIds: list = []
    imageUrl: str = ""


@router.post("/api/tryon")
async def api_tryon(payload: TryonPayload, request: Request, openid: str = Depends(require_openid)):
    item_ids = payload.itemIds or []
    if not item_ids:
        raise HTTPException(status_code=400, detail="缺少单品")
    form = await request.form()
    photos = form.getlist("photos") if hasattr(form, "getlist") else (form.get("photos") or [])
    if not photos:
        raise HTTPException(status_code=400, detail="请上传试穿底图")
    from core.files import save_upload
    photo_path = save_upload(photos[0])
    try:
        return wardrobe_svc.tryon(openid, item_ids, str(photo_path))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
