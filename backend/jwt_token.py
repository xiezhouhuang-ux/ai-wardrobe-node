"""
JWT 登录态工具。

登录流程改为：
  小程序 wx.login -> code -> /api/auth/login -> 后端用 code 换 openid -> 签发 JWT 返回。
  小程序后续请求在 Authorization: Bearer <jwt> 头携带令牌。
  后端校验签名与有效期，从 payload 解出 openid（不再明文传 openid）。

密钥从环境变量 JWT_SECRET 读取；未配置时使用本地开发默认密钥并告警。
"""
import logging
import os
import time

import jwt

logger = logging.getLogger("jwt")

ALGO = "HS256"
EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", str(7 * 24 * 3600)))  # 默认 7 天

# 开发期兜底密钥：未配置 JWT_SECRET 时可用，但生产务必配置环境变量。
_DEV_SECRET = "dev-insecure-jwt-secret-change-me"


def _secret() -> str:
    secret = (os.getenv("JWT_SECRET") or "").strip()
    if not secret:
        logger.warning(
            "JWT_SECRET 未配置，使用不安全默认密钥（仅限本地开发）。"
            "生产环境请设置环境变量 JWT_SECRET。"
        )
        return _DEV_SECRET
    return secret


def create_token(openid: str) -> str:
    """为指定 openid 签发 JWT（HS256，含 exp/iat）。"""
    secret = _secret()
    now = int(time.time())
    payload = {
        "openid": openid,
        "iat": now,
        "exp": now + EXP_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm=ALGO)


def decode_token(token: str) -> str:
    """
    校验 JWT 并返回其中的 openid。
    失败（无令牌 / 签名错误 / 过期 / 解析异常）返回空字符串。
    """
    if not token:
        return ""
    secret = _secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGO])
        return payload.get("openid") or ""
    except Exception as e:  # noqa: BLE001 - 任何失败都视为未登录
        logger.warning("JWT 校验失败: %s", e)
        return ""
