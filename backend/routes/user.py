"""用户接口：上传正面照、上传头像、个人资料。"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from core.deps import require_openid
from core.files import save_upload
import security
from config import WX_APPID
import store

router = APIRouter(tags=["user"])


@router.get("/api/user/photo")
def api_get_user_photo(openid: str = Depends(require_openid)):
    """获取当前用户的全身照信息（复用旧版格式：直接返回 photo dict）。"""
    p = store.get_user_photo(openid)
    if not p:
        raise HTTPException(status_code=404, detail="尚未上传全身照")
    return p


@router.post("/api/user/photo")
async def api_upload_user_photo(request: Request, openid: str = Depends(require_openid)):
    form = await request.form()
    photos = form.getlist("photos") if hasattr(form, "getlist") else (form.get("photos") or [])
    if not photos:
        raise HTTPException(status_code=400, detail="请上传正面照")
    src = save_upload(photos[0])
    # 内容安全检测：上传的全身正面照
    security.check_image(str(src))
    url = f"/uploads/photos/{src.name}"
    store.save_user_photo(openid, url)
    return {"ok": True, "url": url}


class AvatarPayload(BaseModel):
    avatar: str = ""


@router.post("/api/user/avatar")
def api_upload_avatar(payload: AvatarPayload, openid: str = Depends(require_openid)):
    if not payload.avatar:
        raise HTTPException(status_code=400, detail="缺少头像地址")
    store.upsert_user(openid, None, payload.avatar)
    return {"ok": True, "url": payload.avatar}


@router.get("/api/user/profile")
def api_get_profile(openid: str = Depends(require_openid)):
    user = store.get_user(openid)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True, "user": user}
