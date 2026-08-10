"""
认证逻辑：微信 code2session + JWT 签发。路由层调用，不在 app.py 内联。
"""
import logging
import os

import httpx
from config import WX_APPID, WX_SECRET
import jwt_token
import store

logger = logging.getLogger("auth")


def wx_code2session(code: str) -> dict:
    """用小程序登录 code 换取微信 openid。失败抛出异常。"""
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {"appid": WX_APPID, "secret": WX_SECRET, "js_code": code, "grant_type": "authorization_code"}
    try:
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"微信登录接口请求失败: {e}") from e
    if "openid" not in data:
        raise RuntimeError(f"微信登录失败: {data.get('errmsg', data)}")
    return data


def login_with_code(code: str, nickname: str = "", avatar: str = "") -> dict:
    """微信 code 登录：解析 openid -> upsert 用户 -> 签发 JWT。"""
    try:
        wx_info = wx_code2session(code)
    except Exception as e:
        raise RuntimeError(str(e)) from e
    openid = wx_info["openid"]
    store.upsert_user(openid, nickname or "微信用户", avatar)
    token = jwt_token.create_token(openid, role="user")
    return {"ok": True, "token": token, "openid": openid, "role": "user"}


def admin_login(username: str, password: str) -> dict:
    """管理员登录：校验环境变量账号，签发 role=admin 的 JWT。"""
    admin_user = (os.getenv("ADMIN_USER") or "").strip()
    admin_pass = (os.getenv("ADMIN_PASS") or "").strip()
    if not admin_user or not admin_pass:
        raise RuntimeError("服务端未配置管理员账号")
    if username != admin_user or password != admin_pass:
        raise RuntimeError("账号或密码错误")
    token = jwt_token.create_token(f"admin:{admin_user}", role="admin")
    return {"ok": True, "token": token, "role": "admin"}
