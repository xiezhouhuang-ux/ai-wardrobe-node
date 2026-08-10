"""
试穿业务服务：单品快照构建、试穿执行、记录保存。
被 /api/tryon（直接试穿）与 /api/tryon/save（由结果图保存）共用，避免重复。
"""
from typing import Any


import logging
from pathlib import Path

from config import TRYON_RESULTS
import store
from tryon import virtual_tryon
from core.files import new_id, download_image_to

logger = logging.getLogger("tryon_svc")


def build_item_snapshots(openid: str, item_ids: list) -> tuple:
    """
    按 itemId 取真实单品并构建试穿快照。
    返回 (snapshots, missing_ids)。
    - snapshots: [{id, name, category, color, style, imageUrl, imagePath}]
    - missing_ids: 不存在的 id 列表
    """
    found_items = store.get_items_by_ids(item_ids, openid)
    item_map = {it["id"]: it for it in found_items}
    snapshots = []
    missing = []
    for iid in item_ids:
        it = item_map.get(iid)
        if not it:
            missing.append(iid)
            continue
        snap = {
            "id": it["id"],
            "name": it.get("name", ""),
            "category": it.get("category", ""),
            "color": it.get("color", ""),
            "style": it.get("style", ""),
            "imageUrl": it.get("imageUrl",""),
            "imagePath": it.get("imagePath" ,"") 
        }
        snapshots.append(snap)
    return snapshots, missing


def run_tryon(openid: str, item_ids: list, photo_path: str) -> dict:
    """
    执行 AI 试穿。返回 {resultUrl, items}；缺失单品抛 ValueError。
    """
    snapshots, missing = build_item_snapshots(openid, item_ids)
    if missing:
        raise ValueError(f"单品不存在: {', '.join(missing)}")
    if not snapshots:
        raise ValueError("没有有效的单品")

    person_bytes = Path(photo_path).read_bytes()
    # 直接返回 Qwen 生成的 OSS 临时结果地址，不下载到本地
    result_url = virtual_tryon(person_bytes, snapshots)
    return {"resultUrl": result_url, "items": snapshots}


def save_tryon(openid: str, item_ids: list, result_url: str) -> dict:
    """
    由试穿结果图保存记录。单品图在分割阶段已落本地，此处不再下载；
    仅把试穿结果图（result_url）下载到本地 tryon_results/。
    """
    snapshots, missing = build_item_snapshots(openid, item_ids)
    if missing:
        raise ValueError(f"单品不存在: {', '.join(missing)}")

    # 将试穿结果图（result_url，OSS 临时地址）下载到本地 tryon_results/
    if result_url and result_url.startswith("http"):
        out_name = new_id("tr") + ".png"
        out_path = str(Path(TRYON_RESULTS) / out_name)
        if download_image_to(result_url, out_path):
            result_url = f"/uploads/tryon_results/{out_name}"

    record = store.save_tryon_record({
        "openid": openid,
        "itemIds": item_ids,
        "items": snapshots,
        "resultUrl": result_url,
    })
    return record
