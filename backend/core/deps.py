"""
鉴权依赖：供各路由模块共用。普通接口用 require_openid，后台管理用 require_admin。
"""
import jwt_token
from fastapi import HTTPException, Request


def get_openid(request: Request) -> str:
    """从 Authorization 头解析 JWT，返回 openid（无效/缺失返回空串）。"""
    auth = request.headers.get("Authorization", "") or ""
    token = auth[7:].strip() if auth.startswith("Bearer ") else ""
    return jwt_token.decode_token(token)


def require_openid(request: Request) -> str:
    """必须登录：无有效令牌（JWT 校验失败/过期）直接 401。"""
    openid = get_openid(request)
    if not openid:
        raise HTTPException(status_code=401, detail="请先登录")
    return openid


def require_admin(request: Request) -> str:
    """必须管理员：从 JWT 解析 role，非 admin 直接 403。"""
    auth = request.headers.get("Authorization", "") or ""
    token = auth[7:].strip() if auth.startswith("Bearer ") else ""
    payload = jwt_token.decode_token_full(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无管理员权限")
    return payload.get("openid") or ""
