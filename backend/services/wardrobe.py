"""
衣橱业务服务：照片识别、分割预览、单品入库、AI 试穿编排。
路由层只负责参数解析与返回，业务编排集中在此。
"""
import logging
import time
from pathlib import Path

from config import ITEMS
import store
from qwen import detect_clothing
from core.files import new_id, save_upload, download_image_to
from services import tryon_svc

logger = logging.getLogger("wardrobe")


def process_photo(openid: str, files) -> dict:
    """上传全身正面照并识别单品。返回 {photoUrl, items}。"""
    if not files:
        raise ValueError("请上传正面照")
    upload = files[0]
    src = save_upload(upload)
    photo_url = f"/uploads/photos/{src.name}"
    try:
        items = detect_clothing(str(src))
    except Exception as e:  # noqa: BLE001
        logger.exception("识别失败：%s", e)
        items = []
    valid = []
    for idx, it in enumerate(items):
        it["id"] = new_id("it")
        it["createdAt"] = int(time.time() * 1000)
        it["imageUrl"] = f"/uploads/photos/{src.name}"
        it["imagePath"] = str(src)
        valid.append(it)
        if idx >= 9:
            break
    return {"photoUrl": photo_url, "items": valid}


def analyze(openid: str, files) -> dict:
    """拍照/上传服装照，仅用 VL 视觉模型分析候选单品（不分割、不入库）。

    返回 {photoUrl, candidates}，candidates 为识别出的候选单品，
    待用户在 /api/segment 阶段对确认的单品做分割预览。
    """
    if not files:
        raise ValueError("请上传服装照")
    upload = files[0]
    src = save_upload(upload)
    photo_url = f"/uploads/photos/{src.name}"
    try:
        items = detect_clothing(str(src))
    except Exception as e:  # noqa: BLE001
        logger.exception("识别失败：%s", e)
        items = []
    candidates = []
    for idx, it in enumerate(items):
        it["id"] = new_id("it")
        it["imageUrl"] = photo_url
        it["imagePath"] = str(src)
        candidates.append(it)
        if idx >= 9:
            break
    return {"photoUrl": photo_url, "candidates": candidates}


def commit(openid: str, items: list) -> dict:
    """入库单品：远程 OSS 图落地到本地 uploads/items/，写库并返回。"""
    now = int(time.time() * 1000)
    for it in items:
        if not it.get("id"):
            it["id"] = new_id("it")
        it["createdAt"] = now
        img_url = it.get("imageUrl", "")
        if img_url.startswith("http://") or img_url.startswith("https://"):
            out_name = new_id("it") + ".png"
            out_path = str(Path(ITEMS) / out_name)
            if download_image_to(img_url, out_path):
                it["imageUrl"] = f"/uploads/items/{out_name}"
                it["imagePath"] = out_path
    store.add_items(items, openid)
    return {"ok": True, "count": len(items), "items": items}


def tryon(openid: str, item_ids: list, photo_path: str) -> dict:
    """AI 试穿：编排单品快照 + 调用模型 + 结果落地。"""
    return tryon_svc.run_tryon(openid, item_ids, photo_path)


def save_tryon(openid: str, item_ids: list, result_url: str) -> dict:
    """由试穿结果图保存记录。"""
    return tryon_svc.save_tryon(openid, item_ids, result_url)
