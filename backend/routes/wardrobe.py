"""衣橱核心接口：识别、分割预览、入库、AI 试穿。"""
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

from config import UPLOADS_PHOTOS
from core.deps import require_openid
from services import wardrobe as wardrobe_svc
import store
from segment import extract_item

router = APIRouter(tags=["wardrobe"])
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


class SegmentPayload(BaseModel):
    photoUrl: str = ""
    item: dict = {}


@router.post("/api/segment")
def api_segment(payload: SegmentPayload, openid: str = Depends(require_openid)):
    """对确认的单品做分割，返回预览图（不入库）。

    前端传原图 photoUrl（/uploads/photos/...）与 item（含品类/颜色等 meta）。
    """
    if not payload.photoUrl:
        raise HTTPException(status_code=400, detail="缺少原图")
    # /uploads/photos/xxx.png -> 本地 uploads/photos/xxx.png
    photo_url = payload.photoUrl.lstrip("/")
    meta = payload.item
    src_path = str(photo_url)
    if not Path(src_path).exists():
        raise HTTPException(status_code=404, detail="原图不存在")
    try:
        seg = extract_item(src_path, meta or {})
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))

    # 仅返回 Qwen OSS 预览地址，不在本阶段落盘；本地落地交由 /api/commit 完成
    return  {
        **seg,
        "sourcePhoto": payload.photoUrl,
    }



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
async def api_tryon(payload: TryonPayload, openid: str = Depends(require_openid)):
    """直接试穿：底图取当前用户的全身照（按 openid 隔离），无需前端上传。"""
    item_ids = payload.itemIds or []
    if not item_ids:
        raise HTTPException(status_code=400, detail="缺少单品")

    # 取用户全身照（按当前用户隔离）
    photo = store.get_user_photo(openid)
    if not photo or not photo.get("path"):
        raise HTTPException(status_code=400, detail="请先在「我的」上传全身照后再试穿")
    photo_path = photo["path"]
    if not Path(photo_path).exists():
        raise HTTPException(status_code=400, detail="全身照文件不存在，请重新上传")

    try:
        return wardrobe_svc.tryon(openid, item_ids, str(photo_path))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
