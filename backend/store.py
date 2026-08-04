"""
JSON 文件存储模块。复刻原 lib/store.js 的全部方法。
"""
import json
import os
import threading
from pathlib import Path

from config import PATHS

_lock = threading.RLock()

# 历史数据存在中英混排，读取时统一归一到中文规范（不修改磁盘文件）
_CATEGORY_TO_ZH = {"Top": "上衣", "Bottom": "下装", "Shoes": "鞋", "Bag": "包"}
_SEASON_TO_ZH = {
    "Summer": "夏", "Spring": "春", "Autumn": "秋", "Fall": "秋",
    "Winter": "冬", "All": "四季", "Four Seasons": "四季", "四季": "四季",
}
_COLOR_MAP_ZH = {
    "black": "黑", "white": "白", "gray": "灰", "grey": "灰", "beige": "米",
    "khaki": "卡其", "blue": "蓝", "navy": "藏蓝", "denim": "牛仔蓝", "red": "红",
    "green": "绿", "brown": "棕", "pink": "粉", "purple": "紫", "yellow": "黄",
    "orange": "橙", "cream": "米", "camel": "驼", "wine": "酒红", "maroon": "酒红",
    "olive": "橄榄绿", "mint": "薄荷绿", "skyblue": "天蓝", "lightblue": "浅蓝",
    "silver": "银", "gold": "金",
}


def normalize_item_for_api(item: dict) -> dict:
    it = dict(item)
    # 暴露稳定的字符串 id 给前端（详情页跳转依赖 item.id）
    if "_id" in it:
        it["id"] = str(it["_id"])
    cat = it.get("category")
    if cat in _CATEGORY_TO_ZH:
        it["category"] = _CATEGORY_TO_ZH[cat]
    col = it.get("color")
    if isinstance(col, str):
        cl = col.strip().lower()
        if cl in _COLOR_MAP_ZH:
            it["color"] = _COLOR_MAP_ZH[cl]
    season = it.get("season")
    if isinstance(season, list):
        season = season[0] if season else "四季"
        it["season"] = season
    if isinstance(season, str) and season in _SEASON_TO_ZH:
        it["season"] = _SEASON_TO_ZH[season]
    if str(it.get("brand", "")).strip().lower() in ("unknown", "none", "null", ""):
        it["brand"] = ""
    return it


def _read_db() -> dict:
    p = PATHS["WARDROBE_DB"]
    if not os.path.exists(p):
        return {"items": [], "photos": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        return {"items": [], "photos": []}
    if not isinstance(db, dict):
        return {"items": [], "photos": []}
    return db


def _write_db(db: dict) -> None:
    p = PATHS["WARDROBE_DB"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def get_items() -> list:
    with _lock:
        return [normalize_item_for_api(it) for it in _read_db().get("items", [])]


def get_item(item_id: str):
    with _lock:
        for it in _read_db().get("items", []):
            if it.get("id") == item_id:
                return normalize_item_for_api(it)
    return None


def add_items(items: list) -> None:
    with _lock:
        db = _read_db()
        db.setdefault("items", [])
        db["items"].extend(items)
        _write_db(db)


def delete_item(item_id: str) -> bool:
    with _lock:
        db = _read_db()
        items = db.setdefault("items", [])
        idx = next((i for i, it in enumerate(items) if it.get("id") == item_id), None)
        if idx is None:
            return False
        item = items[idx]
        # 删除对应的实体图片文件（优先用绝对路径 imagePath，回退到 imageUrl）
        removed = items.pop(idx)
        img_path = removed.get("imagePath") or _url_to_path(removed.get("imageUrl"))
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except OSError:
                pass
        _write_db(db)
        return True


def add_photo(photo: dict) -> None:
    with _lock:
        db = _read_db()
        db.setdefault("photos", [])
        db["photos"].append(photo)
        _write_db(db)


def get_photos() -> list:
    with _lock:
        return list(_read_db().get("photos", []))


def get_stats() -> dict:
    with _lock:
        items = _read_db().get("items", [])
    cats = {}
    for it in items:
        c = it.get("category")
        if c:
            cats[c] = cats.get(c, 0) + 1
    return {"total": len(items), "byCategory": cats}


def _url_to_path(url: str):
    if not url:
        return None
    # 形如 /items/xxx.png 或 /uploads/xxx.jpg
    rel = url.split("?", 1)[0].lstrip("/")
    return os.path.join(PATHS["ROOT"], rel)


# ---------------- 日历穿搭（outfits） ----------------

def get_outfits() -> list:
    """返回全部日历穿搭记录。"""
    with _lock:
        return list(_read_db().get("outfits", []))


def get_outfit(date: str):
    """按日期（YYYY-MM-DD）取当天穿搭，不存在返回 None。"""
    with _lock:
        for o in _read_db().get("outfits", []):
            if o.get("date") == date:
                return o
    return None


def save_outfit(outfit: dict) -> dict:
    """新增或更新某天的穿搭（按 date upsert）。返回保存后的记录。"""
    with _lock:
        db = _read_db()
        db.setdefault("outfits", [])
        date = outfit.get("date")
        idx = next((i for i, o in enumerate(db["outfits"]) if o.get("date") == date), None)
        if idx is None:
            db["outfits"].append(outfit)
        else:
            db["outfits"][idx] = outfit
        _write_db(db)
        return outfit


def delete_outfit(date: str) -> bool:
    """删除某天的穿搭记录。"""
    with _lock:
        db = _read_db()
        outfits = db.setdefault("outfits", [])
        idx = next((i for i, o in enumerate(outfits) if o.get("date") == date), None)
        if idx is None:
            return False
        outfits.pop(idx)
        _write_db(db)
        return True


# ---------------- 用户照片（全身试穿底图） ----------------

def get_user_photo() -> dict | None:
    """获取当前用户的全身照元信息，不存在返回 None。"""
    with _lock:
        return _read_db().get("userPhoto")


def save_user_photo(photo: dict) -> None:
    """保存/更新用户全身照元信息。"""
    with _lock:
        db = _read_db()
        db["userPhoto"] = photo
        _write_db(db)


# ---------------- 试穿记录 ----------------

def get_tryon_records() -> list:
    """获取全部试穿记录，按时间倒序。"""
    with _lock:
        records = list(_read_db().get("tryonRecords", []))
        records.sort(key=lambda r: r.get("createdAt", 0), reverse=True)
        return records


def save_tryon_record(record: dict) -> dict:
    """保存一条试穿记录。"""
    with _lock:
        db = _read_db()
        db.setdefault("tryonRecords", [])
        db["tryonRecords"].append(record)
        _write_db(db)
        return record


def delete_tryon_record(record_id: str) -> bool:
    """删除一条试穿记录（同时删除本地结果图）。"""
    with _lock:
        db = _read_db()
        records = db.setdefault("tryonRecords", [])
        idx = next((i for i, r in enumerate(records) if r.get("id") == record_id), None)
        if idx is None:
            return False
        removed = records.pop(idx)
        # 删除本地结果图
        img_path = removed.get("imagePath")
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except OSError:
                pass
        _write_db(db)
        return True
