"""认证接口：微信登录、管理员登录。"""
from fastapi import APIRouter, Body, HTTPException

from core import auth as auth_core

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login")
def api_auth_login(body: dict = Body(default={})):
    code = body.get("code") or ""
    nickname = body.get("nickname") or ""
    avatar = body.get("avatar") or ""
    if not code:
        raise HTTPException(status_code=400, detail="缺少 code")
    try:
        return auth_core.login_with_code(code, nickname, avatar)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/admin/login")
def api_admin_login(body: dict = Body(default={})):
    username = body.get("username") or ""
    password = body.get("password") or ""
    try:
        return auth_core.admin_login(username, password)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=str(e))
