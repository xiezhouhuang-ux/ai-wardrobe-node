"""
文件工具：上传保存、唯一 ID、图片 URL 解析与落盘。
原 app.py 中散落的 _new_id / _save_upload / 图片路径解析逻辑统一收敛到此，
供路由层、试穿/分割服务共用，避免重复。
"""
import uuid
from pathlib import Path

from config import ROOT, ITEMS, TRYON_RESULTS, UPLOADS, UPLOADS_PHOTOS
from segment import normalize_to_png, download_to_local as _segment_download


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


def resolve_image_path(item: dict) -> str:
    """
    从单品 dict 解析出可读取的本地图片路径。
    优先 imagePath；其次 imageUrl 以 '/' 开头则相对 ROOT 拼接。
    """
    img_path = item.get("imagePath") or ""
    if not img_path and (item.get("imageUrl") or "").startswith("/"):
        img_path = str(Path(ROOT) / item["imageUrl"].lstrip("/"))
    return img_path


def download_image_to(url: str, out_path: str) -> bool:
    """
    将 http(s) / 本地相对 URL 的图片下载并规范化为白底 PNG 落到 out_path。
    成功返回 True，失败返回 False（仅记录日志，不抛异常）。
    """
    try:
        if url.startswith("http://") or url.startswith("https://"):
            # download_to_local 内部已自行做 PNG 规范化，这里只传 url 与落盘路径
            _segment_download(url, out_path)
        elif url.startswith("/uploads/items/"):
            src = Path(ROOT) / url.lstrip("/")
            if src.exists():
                Path(out_path).write_bytes(normalize_to_png(src.read_bytes()))
        else:
            return False
        return True
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger("files").exception("图片落地失败 %s -> %s: %s", url, out_path, e)
        return False
