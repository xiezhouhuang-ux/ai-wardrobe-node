"""后台管理接口：统计、跨用户分页查询、删除（需管理员角色）。"""
from fastapi import APIRouter, Depends, HTTPException

from core.deps import require_admin
import store

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def api_admin_stats(admin: str = Depends(require_admin)):
    return store.get_admin_stats()


@router.get("/items")
def api_admin_items(page: int = 1, size: int = 20, keyword: str = "", admin: str = Depends(require_admin)):
    return store.list_all_items(page=page, size=size, keyword=keyword)


@router.delete("/items/{item_id}")
def api_admin_delete_item(item_id: str, admin: str = Depends(require_admin)):
    if not store.delete_item(item_id):
        raise HTTPException(status_code=404, detail="单品不存在")
    return {"ok": True}


@router.get("/tryon")
def api_admin_tryon(page: int = 1, size: int = 20, admin: str = Depends(require_admin)):
    return store.list_all_tryon(page=page, size=size)


@router.delete("/tryon/{record_id}")
def api_admin_delete_tryon(record_id: str, admin: str = Depends(require_admin)):
    if not store.delete_tryon_record(record_id):
        raise HTTPException(status_code=404, detail="试穿记录不存在")
    return {"ok": True}


@router.get("/outfits")
def api_admin_outfits(page: int = 1, size: int = 20, admin: str = Depends(require_admin)):
    return store.list_all_outfits(page=page, size=size)


@router.delete("/outfits/{date}")
def api_admin_delete_outfit(date: str, admin: str = Depends(require_admin)):
    if not store.delete_outfit(date):
        raise HTTPException(status_code=404, detail="搭配记录不存在")
    return {"ok": True}


@router.get("/users")
def api_admin_users(page: int = 1, size: int = 20, keyword: str = "", admin: str = Depends(require_admin)):
    """后台：分页查询用户列表。"""
    return store.list_all_users(page=page, size=size, keyword=keyword)
