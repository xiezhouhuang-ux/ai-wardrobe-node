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
def api_list_items(openid: str = Depends(require_openid), target: str = ""):
    """列出衣橱单品；不传 target 时返回当前用户，传 target 时返回指定用户（管理视角）。"""
    q = target or openid
    return store.get_items(q)


@router.get("/api/users")
def api_list_users(page: int = 1, size: int = 200, keyword: str = "", openid: str = Depends(require_openid)):
    """列出所有用户（管理视角，供前端切换用户衣橱试穿）。

    排除当前登录用户本人（本人由前端单独置顶展示，信息取自登录态）。
    返回额外携带 self 字段（含 openid，供前端跳转衣橱试穿时使用）。
    """
    # 在 SQL 层直接排除当前用户本人，无需循环过滤
    result = store.list_all_users(page=page, size=size, keyword=keyword, exclude_openid=openid)
    me = store.get_user(openid) or {"openid": openid, "nickname": "", "avatar": ""}
    # selfOpenid 直接取自 JWT 解析出的 openid，必定可靠，供前端跳转衣橱试穿使用
    result["self"] = me
    result["selfOpenid"] = openid
    return result


@router.get("/api/items/{item_id}")
def api_get_item(item_id: str, openid: str = Depends(require_openid)):
    """小程序端：获取单个单品详情。"""
    item = store.get_item(item_id)
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
    target: str = ""


@router.post("/api/tryon")
async def api_tryon(payload: TryonPayload, openid: str = Depends(require_openid)):
    """直接试穿：底图取目标用户的全身照（target 缺省为当前用户），无需前端上传。"""
    item_ids = payload.itemIds or []
    if not item_ids:
        raise HTTPException(status_code=400, detail="缺少单品")

    # 管理视角下可指定被试穿用户；缺省为当前登录用户
    target = (payload.target and str(payload.target).strip()) or openid

    # 取用户全身照（按目标用户隔离）
    photo = store.get_user_photo(target)
    if not photo or not photo.get("path"):
        raise HTTPException(status_code=400, detail="该用户尚未上传全身照，无法试穿")
    photo_path = photo["path"]
    if not Path(photo_path).exists():
        raise HTTPException(status_code=400, detail="全身照文件不存在，请重新上传")

    try:
        return wardrobe_svc.tryon(target, item_ids, str(photo_path))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
