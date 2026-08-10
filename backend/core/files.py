"""
文件工具：上传保存、唯一 ID、图片 URL 解析与落盘。
原 app.py 中散落的 _new_id / _save_upload / 图片路径解析逻辑统一收敛到此，
供路由层、试穿/分割服务共用，避免重复。
"""
import uuid
from pathlib import Path

import requests

from config import ROOT, ITEMS, TRYON_RESULTS, UPLOADS, UPLOADS_PHOTOS


def new_id(prefix: str = "id") -> str:
    """生成带前缀的唯一 ID。"""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def save_upload(upload) -> Path:
    """保存上传文件到 uploads/photos/，返回保存后的 Path。"""
    suffix = "png"
    try:
        if upload.filename and "." in upload.filename:
            suffix = upload.filename.rsplit(".", 1)[-1].lower()
    except Exception:
        pass
    name = f"{uuid.uuid4().hex}.{suffix}"
    dest = Path(UPLOADS_PHOTOS) / name
    dest.write_bytes(upload.file.read())
    return dest

def download_image_to(url: str, out_path: str) -> bool:
    """
    将 http(s) / 本地相对 URL 的图片直接下载/拷贝到本地 out_path（不做 PNG 转换/白底规整）。
    成功返回 True，失败返回 False（仅记录日志，不抛异常）。
    """
    try:
        if url.startswith("http://") or url.startswith("https://"):
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Wardrobe/1.0)"},
                timeout=120,
            )
            resp.raise_for_status()
            Path(out_path).write_bytes(resp.content)
        else:
            return False
        return True
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger("files").exception("图片落地失败 %s -> %s: %s", url, out_path, e)
        return False
