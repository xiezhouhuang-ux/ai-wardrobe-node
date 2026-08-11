"""用户接口：上传正面照、上传头像、个人资料。"""
import time

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
async def api_upload_user_photo(photo: UploadFile = File(..., description="全身正面照"), openid: str = Depends(require_openid)):
    src = save_upload(photo)
    try:
        security.check_image(str(src))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=f"内容未通过安全检测: {pe}")
    # 内容安全检测：上传的全身正面照
    url = f"/uploads/photos/{src.name}"
    info = {
        "openid": openid,
        "url": url,
        "path": str(src),
        "createdAt": int(time.time() * 1000),
    }
    store.save_user_photo(info)
    
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


class ProfilePayload(BaseModel):
    nickname: str = ""
    avatar: str = ""


@router.post("/api/user/profile")
def api_update_profile(payload: ProfilePayload, openid: str = Depends(require_openid)):
    """更新当前用户的昵称与头像（仅传入非空字段才覆盖）。"""
    if not payload.nickname and not payload.avatar:
        raise HTTPException(status_code=400, detail="nickname 与 avatar 至少传入一项")
    # 昵称为用户输入，需过内容安全检测
    if payload.nickname:
        try:
            security.check_text(payload.nickname, scene=2, openid=openid)
        except security.ContentRiskError as cre:
            raise HTTPException(status_code=403, detail=str(cre.message))
    store.upsert_user(openid, payload.nickname, payload.avatar)
    return {"ok": True, "user": store.get_user(openid)}
