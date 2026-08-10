"""
试穿业务服务：单品快照构建、试穿执行、记录保存。
被 /api/tryon（直接试穿）与 /api/tryon/save（由结果图保存）共用，避免重复。
"""
import logging
from pathlib import Path

from config import ROOT, TRYON_RESULTS, ITEMS
import store
from tryon import virtual_tryon, download_to_local as _tryon_download
from core.files import new_id, resolve_image_path, download_image_to

logger = logging.getLogger("tryon_svc")


def build_item_snapshots(openid: str, item_ids: list) -> tuple:
    """
    按 itemId 取真实单品并构建试穿快照。
    返回 (snapshots, missing_ids)。
    - snapshots: [{id, name, category, color, style, imageUrl, imagePath}]
    - missing_ids: 不存在的 id 列表
    """
    all_items = store.get_items(openid)
    item_map = {it["id"]: it for it in all_items}
    snapshots = []
    missing = []
    for iid in item_ids:
        it = item_map.get(iid)
        if not it:
            missing.append(iid)
            continue
        img_path = resolve_image_path(it)
        snap = {
            "id": it["id"],
            "name": it.get("name", ""),
            "category": it.get("category", ""),
            "color": it.get("color", ""),
            "style": it.get("style", ""),
            "imageUrl": it.get("imageUrl") or (f"/uploads/items/{Path(img_path).name}" if img_path else ""),
            "imagePath": img_path,
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
    result_url = virtual_tryon(person_bytes, snapshots)
    out_name = new_id("tr") + ".png"
    out_path = str(Path(TRYON_RESULTS) / out_name)
    _tryon_download(result_url, out_path)
    result_url = f"/uploads/tryon_results/{out_name}"
    return {"resultUrl": result_url, "items": snapshots}


def save_tryon(openid: str, item_ids: list, result_url: str) -> dict:
    """
    由试穿结果图保存记录。单品图按需落地到本地 items/，返回保存的记录。
    """
    snapshots, missing = build_item_snapshots(openid, item_ids)
    if missing:
        raise ValueError(f"单品不存在: {', '.join(missing)}")

    for it in snapshots:
        url = it.get("imageUrl") or ""
        if (not it.get("imagePath")) and (url.startswith("http://") or url.startswith("https://")):
            out_name = new_id("it") + ".png"
            out_path = str(Path(ITEMS) / out_name)
            if download_image_to(url, out_path):
                it["imageUrl"] = f"/uploads/items/{out_name}"
                it["imagePath"] = out_path
    record = store.save_tryon_record({
        "openid": openid,
        "items": snapshots,
        "resultUrl": result_url,
    })
    record["items"] = snapshots
    return record
