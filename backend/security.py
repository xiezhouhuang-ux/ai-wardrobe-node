"""
微信小程序内容安全检测模块。

覆盖小程序内所有"对外发布"场景：
  - 文本：security.msgSecCheck（评论、备注、昵称等用户输入）
  - 图片：security.imgSecCheck（上传的全身照、衣橱单品图、试穿结果图等）

说明：
  - access_token 自动获取并缓存（提前 5 分钟刷新），避免反复请求。
  - 当未配置 WX_APPID / WX_SECRET 时，自动降级为"放行"（DEMO 模式），
    保证本地开发与无小程序资质时流程不中断。
  - 检测命中违规时，抛出异常，由调用方统一返回"内容含违规信息"。
"""
import json
import logging
import threading
import time

import requests

import config

logger = logging.getLogger("security")

# access_token 缓存
_token = {"value": None, "expire_at": 0}
_token_lock = threading.Lock()

# 微信接口地址
_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
_MSG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
_IMG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/img_sec_check"

# 图片大小 / 类型限制（微信要求 <= 1MB，jpg/png）
_MAX_IMG_BYTES = 1 * 1024 * 1024
_ALLOWED_IMG_EXT = {".jpg", ".jpeg", ".png"}


def _is_enabled() -> bool:
    return bool(config.WX_APPID) and bool(config.WX_SECRET)


def _get_access_token() -> str:
    """获取 access_token，带进程内缓存。"""
    now = time.time()
    if _token["value"] and now < _token["expire_at"]:
        return _token["value"]

    with _token_lock:
        # 双重检查
        if _token["value"] and now < _token["expire_at"]:
            return _token["value"]
        resp = requests.get(
            _TOKEN_URL,
            params={
                "grant_type": "client_credential",
                "appid": config.WX_APPID,
                "secret": config.WX_SECRET,
            },
            timeout=10,
        )
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data}")
        # 微信返回的是秒级有效期，提前 5 分钟过期
        expires_in = int(data.get("expires_in", 7200))
        _token["value"] = data["access_token"]
        _token["expire_at"] = now + max(0, expires_in - 300)
        logger.info("已获取微信 access_token，有效期 %s 秒", expires_in)
        return _token["value"]


class ContentRiskError(Exception):
    """内容命中违规时抛出，detail 即为给前端/用户的提示文案。"""
    def __init__(self, message: str = "所发布内容含违规信息", field: str = ""):
        super().__init__(message)
        self.message = message
        self.field = field


def check_text(content: str, scene: int = 2, openid: str = "") -> None:
    """
    检测文本是否违规。违规则抛 ContentRiskError。

    :param content: 待检测文本（备注、昵称等）
    :param scene: 场景值，2=资料（默认对外展示），1=评论
    :param openid: 用户 openid（建议传入，便于微信风控）
    """
    if not content or not content.strip():
        return
    if not _is_enabled():
        logger.info("内容安全未启用（未配置 AppID/Secret），文本检测放行: %r", content[:20])
        return

    token = _get_access_token()
    payload = {
        "content": content,
        "version": "2",
        "scene": scene,
    }
    if openid:
        payload["openid"] = openid

    resp = requests.post(
        f"{_MSG_SEC_CHECK_URL}?access_token={token}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    data = resp.json()
    logger.info("文本检测 status=%s result=%s", resp.status_code, str(data)[:300])

    # errcode=0 通过；87014 内容违规；其他按需处理
    if data.get("errcode") == 87014:
        raise ContentRiskError("所发布内容含违规信息", field="text")
    if data.get("errcode") not in (0,):
        # 其他错误码（如 token 失效）记录但不阻断正常发布流程
        logger.warning("文本检测返回非预期 errcode=%s", data.get("errcode"))


def check_image(image_path: str, openid: str = "") -> None:
    """
    检测图片是否违规。违规则抛 ContentRiskError。

    :param image_path: 本地图片路径（jpg/png，<=1MB）
    :param openid: 用户 openid
    """
    if not image_path or not _is_enabled():
        if not _is_enabled():
            logger.info("内容安全未启用，图片检测放行: %s", image_path)
        return

    from pathlib import Path
    p = Path(image_path)
    if not p.exists():
        logger.warning("待检测图片不存在，跳过: %s", image_path)
        return

    # 超过 1MB 时压缩到阈值内（避免微信接口报错）
    data = p.read_bytes()
    ext = p.suffix.lower()
    if ext not in _ALLOWED_IMG_EXT:
        # 非 jpg/png 尝试转码为 jpg
        data = _to_jpg(data)
    if len(data) > _MAX_IMG_BYTES:
        data = _resize_to_limit(data, _MAX_IMG_BYTES)

    token = _get_access_token()
    resp = requests.post(
        f"{_IMG_SEC_CHECK_URL}?access_token={token}",
        files={"media": (p.name, data, "image/jpeg")},
        timeout=10,
    )
    result = resp.json()
    logger.info("图片检测 status=%s result=%s", resp.status_code, str(result)[:300])

    if result.get("errcode") == 87014:
        raise ContentRiskError("所发布内容含违规信息", field="image")


def _to_jpg(raw: bytes) -> bytes:
    """将任意图片 bytes 转码为 jpg。"""
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(raw)).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        logger.warning("图片转码失败，原样返回: %s", e)
        return raw


def _resize_to_limit(raw: bytes, limit: int) -> bytes:
    """按比例缩小图片直到 <= limit。"""
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(raw))
        quality = 90
        while True:
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            out = buf.getvalue()
            if len(out) <= limit or quality <= 20:
                return out
            quality -= 10
    except Exception as e:
        logger.warning("图片压缩失败，原样返回: %s", e)
        return raw
