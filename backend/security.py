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
# 注：access_token 改用「稳定版接口」stable_token，它与普通 token 接口互斥、
# 不会互相强制失效，更适合多实例/后台刷新场景（避免 40001 invalid credential）。
_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/stable_token"
_MSG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
_IMG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/img_sec_check"

# 图片大小 / 类型限制（微信要求 <= 1MB，jpg/png）
_MAX_IMG_BYTES = 1 * 1024 * 1024
_ALLOWED_IMG_EXT = {".jpg", ".jpeg", ".png"}


def _is_enabled() -> bool:
    return bool(config.WX_APPID) and bool(config.WX_SECRET)


# token 相关错误码：需强制刷新 access_token 后重试
_TOKEN_ERRCODES = {40001, 40014, 41001, 42001}


def _fetch_token() -> str:
    """向微信请求新的 access_token（不带缓存，使用稳定版接口 stable_token）。"""
    now = time.time()
    resp = requests.post(
        _TOKEN_URL,
        json={
            "grant_type": "client_credential",
            "appid": config.WX_APPID,
            "secret": config.WX_SECRET,
            # force_refresh=false 由微信侧协调，多个服务不会互相强制失效 token
            "force_refresh": False,
        },
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"获取 access_token 失败: {data}")
    # 稳定版接口返回 access_token_expire_in（秒级），提前 5 分钟过期
    expires_in = int(data.get("access_token_expire_in", data.get("expires_in", 7200)))
    _token["value"] = data["access_token"]
    _token["expire_at"] = now + max(0, expires_in - 300)
    logger.info("已获取微信 access_token（stable），有效期 %s 秒", expires_in)
    return _token["value"]


def _get_access_token(force: bool = False) -> str:
    """获取 access_token，带进程内缓存。force=True 时忽略缓存强制刷新。"""
    now = time.time()
    if not force and _token["value"] and now < _token["expire_at"]:
        return _token["value"]

    with _token_lock:
        # 双重检查（仅非强制刷新时）
        if not force and _token["value"] and now < _token["expire_at"]:
            return _token["value"]
        return _fetch_token()


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

    # access_token 失效类错误：强制刷新 token 后重试一次
    if data.get("errcode") in _TOKEN_ERRCODES:
        logger.warning("文本检测 access_token 失效(%s)，刷新后重试", data.get("errcode"))
        token = _get_access_token(force=True)
        resp = requests.post(
            f"{_MSG_SEC_CHECK_URL}?access_token={token}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        data = resp.json()
        logger.info("文本检测(重试) status=%s result=%s", resp.status_code, str(data)[:300])

    # errcode=0 通过；87014 内容违规；其他按需处理
    if data.get("errcode") == 87014:
        raise ContentRiskError("所发布内容含违规信息", field="text")
    if data.get("errcode") not in (0,):
        # 其他错误码（如 token 仍异常）记录但不阻断正常发布流程
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

    # access_token 失效类错误：强制刷新 token 后重试一次
    if result.get("errcode") in _TOKEN_ERRCODES:
        logger.warning("图片检测 access_token 失效(%s)，刷新后重试", result.get("errcode"))
        token = _get_access_token(force=True)
        resp = requests.post(
            f"{_IMG_SEC_CHECK_URL}?access_token={token}",
            files={"media": (p.name, data, "image/jpeg")},
            timeout=10,
        )
        result = resp.json()
        logger.info("图片检测(重试) status=%s result=%s", resp.status_code, str(result)[:300])

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
