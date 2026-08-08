"""
MySQL 存储模块。复刻原 lib/store.js 的全部方法。

数据库表结构：
  - items        衣橱单品
  - photos       上传的原始照片
  - outfits      日历穿搭
  - user_photo   用户全身照（单行）
  - tryon_records 试穿记录
"""
import json
import logging
import os
import threading
import time
from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

import config
from config import MYSQL_CONFIG

logger = logging.getLogger("store")

_conn_lock = threading.Lock()


def _get_conn():
    """获取一个数据库连接（线程安全；当前每次新建连接，避免依赖连接池扩展）。"""
    # 每次新建连接并设 autocommit，简单可靠
    conn = pymysql.connect(cursorclass=DictCursor, **MYSQL_CONFIG)
    conn.autocommit_mode = True
    return conn


# 历史数据存在中英混排，读取时统一归一到中文规范（不修改数据库）
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
    # 兜底：历史数据可能既无 _id 也无 id，读取时务必保证有 id
    if not it.get("id"):
        import time as _t
        it["id"] = f"it_{int(_t.time() * 1000)}"
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


# ---------------- 衣橱单品 ----------------

def _row_to_item(row: dict) -> dict:
    """将数据库行转换为 API 规范 dict（JSON 字段解析）。"""
    item = {
        "id": row["id"],
        "category": row.get("category") or "",
        "color": row.get("color") or "",
        "season": row.get("season") or "四季",
        "material": row.get("material") or "",
        "style": row.get("style") or "",
        "fit": row.get("fit") or "",
        "pattern": row.get("pattern") or "",
        "brand": row.get("brand") or "",
        "hasLogo": bool(row.get("has_logo")),
        "imageUrl": row.get("image_url") or "",
        "imagePath": row.get("image_path") or "",
        "transparent": bool(row.get("transparent")),
        "segmentMethod": row.get("segment_method") or "",
        "sourcePhoto": row.get("source_photo") or "",
        "createdAt": int(row.get("created_at", 0) or 0),
    }
    return normalize_item_for_api(item)


def get_items(openid: str = "") -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM items WHERE openid=%s ORDER BY created_at DESC", (openid,))
            else:
                cur.execute("SELECT * FROM items ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [_row_to_item(r) for r in rows]


def get_item(item_id: str, openid: str = ""):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM items WHERE id=%s AND openid=%s", (item_id, openid))
            else:
                cur.execute("SELECT * FROM items WHERE id=%s", (item_id,))
            row = cur.fetchone()
    if not row:
        return None
    return _row_to_item(row)


def add_items(items: list, openid: str = "") -> None:
    if not items:
        return
    cols = (
        "id", "openid", "category", "color", "season", "material", "style", "fit",
        "pattern", "brand", "has_logo", "image_url", "image_path",
        "transparent", "segment_method", "source_photo", "created_at",
    )
    sql = (
        "INSERT INTO items ("
        + ", ".join(cols)
        + ") VALUES ("
        + ", ".join(["%s"] * len(cols))
        + ") ON DUPLICATE KEY UPDATE "
        + ", ".join(f"{c}=VALUES({c})" for c in cols if c != "id")
    )
    with _get_conn() as conn:
        with conn.cursor() as cur:
            for it in items:
                cur.execute(sql, (
                    it.get("id"),
                    openid,
                    it.get("category", ""),
                    it.get("color", ""),
                    it.get("season", "四季"),
                    it.get("material", ""),
                    it.get("style", ""),
                    it.get("fit", ""),
                    it.get("pattern", ""),
                    it.get("brand", ""),
                    1 if it.get("hasLogo") else 0,
                    it.get("imageUrl", ""),
                    it.get("imagePath", ""),
                    1 if it.get("transparent") else 0,
                    it.get("segmentMethod", ""),
                    it.get("sourcePhoto", ""),
                    int(it.get("createdAt", 0) or 0),
                ))
        conn.commit()


def delete_item(item_id: str, openid: str = "") -> bool:
    # 删除对应的实体图片文件
    item = get_item(item_id, openid)
    img_path = None
    if item:
        img_path = item.get("imagePath") or (
            str(Path(config.ROOT) / item["imageUrl"].lstrip("/"))
            if (item.get("imageUrl") or "").startswith("/") else None
        )
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("DELETE FROM items WHERE id=%s AND openid=%s", (item_id, openid))
            else:
                cur.execute("DELETE FROM items WHERE id=%s", (item_id,))
            affected = cur.rowcount
        conn.commit()
    if affected and img_path and os.path.exists(img_path):
        try:
            os.remove(img_path)
        except OSError:
            pass
    return bool(affected)


def get_stats(openid: str = "") -> dict:
    cats = {}
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute(
                    "SELECT category, COUNT(*) AS cnt FROM items WHERE openid=%s GROUP BY category",
                    (openid,),
                )
            else:
                cur.execute("SELECT category, COUNT(*) AS cnt FROM items GROUP BY category")
            rows = cur.fetchall()
    for r in rows:
        c = r["category"] or "未分类"
        cats[c] = cats.get(c, 0) + r["cnt"]
    total = sum(cats.values())
    return {"total": total, "byCategory": cats}


# ---------------- 原始照片（uploads 历史） ----------------

def add_photo(photo: dict, openid: str = "") -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO photos (id, openid, url, created_at) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE openid=VALUES(openid), url=VALUES(url), created_at=VALUES(created_at)",
                (photo.get("id"), openid, photo.get("url"), int(photo.get("createdAt", 0) or 0)),
            )
        conn.commit()


def get_photos(openid: str = "") -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM photos WHERE openid=%s ORDER BY created_at DESC", (openid,))
            else:
                cur.execute("SELECT * FROM photos ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [
        {"id": r["id"], "url": r["url"], "createdAt": int(r.get("created_at", 0) or 0)}
        for r in rows
    ]


# ---------------- 日历穿搭（outfits） ----------------

def get_outfits(openid: str = "") -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM outfits WHERE openid=%s ORDER BY date DESC", (openid,))
            else:
                cur.execute("SELECT * FROM outfits ORDER BY date DESC")
            rows = cur.fetchall()
    return [_row_to_outfit(r) for r in rows]


def get_outfit(date: str, openid: str = ""):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM outfits WHERE date=%s AND openid=%s", (date, openid))
            else:
                cur.execute("SELECT * FROM outfits WHERE date=%s", (date,))
            row = cur.fetchone()
    return _row_to_outfit(row) if row else None


def _row_to_outfit(row: dict) -> dict:
    items = []
    try:
        items = json.loads(row["items_json"]) if row.get("items_json") else []
    except Exception:
        items = []
    return {
        "date": row["date"],
        "openid": row.get("openid") or "",
        "items": items,
        "note": row.get("note") or "",
        "updatedAt": int(row.get("updated_at", 0) or 0),
    }


def save_outfit(outfit: dict) -> dict:
    date = outfit.get("date")
    openid = outfit.get("openid", "")
    items_json = json.dumps(outfit.get("items", []), ensure_ascii=False)
    note = outfit.get("note", "")
    updated_at = int(outfit.get("updatedAt", 0) or 0)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO outfits (date, openid, items_json, note, updated_at) VALUES (%s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE openid=VALUES(openid), items_json=VALUES(items_json), "
                "note=VALUES(note), updated_at=VALUES(updated_at)",
                (date, openid, items_json, note, updated_at),
            )
        conn.commit()
    return outfit


def delete_outfit(date: str, openid: str = "") -> bool:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("DELETE FROM outfits WHERE date=%s AND openid=%s", (date, openid))
            else:
                cur.execute("DELETE FROM outfits WHERE date=%s", (date,))
            affected = cur.rowcount
        conn.commit()
    return bool(affected)


# ---------------- 用户照片（全身试穿底图） ----------------

def get_user_photo(openid: str = "") -> dict | None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM user_photo WHERE openid=%s", (openid,))
            else:
                cur.execute("SELECT * FROM user_photo LIMIT 1")
            row = cur.fetchone()
    if not row:
        return None
    return {
        "openid": row.get("openid") or "",
        "url": row.get("url") or "",
        "path": row.get("path") or "",
        "createdAt": int(row.get("created_at", 0) or 0),
    }


def save_user_photo(photo: dict) -> None:
    openid = photo.get("openid", "")
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # 按 openid upsert
            cur.execute(
                "INSERT INTO user_photo (openid, url, path, created_at) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE url=VALUES(url), path=VALUES(path), created_at=VALUES(created_at)",
                (openid, photo.get("url"), photo.get("path"), int(photo.get("createdAt", 0) or 0)),
            )
        conn.commit()


# ---------------- 试穿记录 ----------------

def get_tryon_records(openid: str = "") -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM tryon_records WHERE openid=%s ORDER BY created_at DESC", (openid,))
            else:
                cur.execute("SELECT * FROM tryon_records ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [_row_to_tryon(r) for r in rows]


def _row_to_tryon(row: dict) -> dict:
    items = []
    try:
        items = json.loads(row["items_json"]) if row.get("items_json") else []
    except Exception:
        items = []
    return {
        "id": row["id"],
        "openid": row.get("openid") or "",
        "itemIds": json.loads(row["item_ids_json"]) if row.get("item_ids_json") else [],
        "items": items,
        "resultUrl": row.get("result_url") or "",
        "imagePath": row.get("image_path") or "",
        "createdAt": int(row.get("created_at", 0) or 0),
    }


def save_tryon_record(record: dict) -> dict:
    openid = record.get("openid", "")
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tryon_records (id, openid, item_ids_json, items_json, result_url, image_path, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE openid=VALUES(openid), item_ids_json=VALUES(item_ids_json), "
                "items_json=VALUES(items_json), result_url=VALUES(result_url), "
                "image_path=VALUES(image_path), created_at=VALUES(created_at)",
                (
                    record.get("id"),
                    openid,
                    json.dumps(record.get("itemIds", []), ensure_ascii=False),
                    json.dumps(record.get("items", []), ensure_ascii=False),
                    record.get("resultUrl", ""),
                    record.get("imagePath", ""),
                    int(record.get("createdAt", 0) or 0),
                ),
            )
        conn.commit()
    return record


def delete_tryon_record(record_id: str, openid: str = "") -> bool:
    # 删除本地结果图
    record = None
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM tryon_records WHERE id=%s AND openid=%s", (record_id, openid))
            else:
                cur.execute("SELECT * FROM tryon_records WHERE id=%s", (record_id,))
            row = cur.fetchone()
            if row:
                record = _row_to_tryon(row)
            if openid:
                cur.execute("DELETE FROM tryon_records WHERE id=%s AND openid=%s", (record_id, openid))
            else:
                cur.execute("DELETE FROM tryon_records WHERE id=%s", (record_id,))
            affected = cur.rowcount
        conn.commit()
    if affected and record:
        img_path = record.get("imagePath")
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except OSError:
                pass
    return bool(affected)


# ---------------- 数据库初始化 ----------------

def _ensure_openid_column(cur, table: str, not_null: bool = True) -> None:
    """若旧表没有 openid 列则补上（幂等；依赖于 information_schema）。

    :param not_null: user_photo 表的 openid 是主键，但若是旧表补列时可能已有
                     数据行，此时用可空列避免 ALTER 失败；其它表用 NOT NULL DEFAULT ''。
    """
    try:
        cur.execute(
            "SELECT COUNT(*) AS c FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name=%s AND column_name='openid'",
            (table,),
        )
        row = cur.fetchone()
        if not row or (row.get("c") or row.get("COUNT(*)") or 0) == 0:
            if not_null:
                cur.execute(
                    f"ALTER TABLE `{table}` ADD COLUMN openid VARCHAR(64) NOT NULL DEFAULT ''"
                )
            else:
                cur.execute(
                    f"ALTER TABLE `{table}` ADD COLUMN openid VARCHAR(64) NULL"
                )
            cur.execute(
                f"ALTER TABLE `{table}` ADD INDEX idx_openid (openid)"
            )
    except Exception as e:
        logger.warning("为表 %s 补 openid 列失败（可忽略）: %s", table, e)


def init_db() -> None:
    """创建数据库和所有表（如果不存在）。"""
    cfg = dict(MYSQL_CONFIG)
    db_name = cfg.pop("database")
    # 先连到 MySQL 服务端（不含 database）创建库
    init_cfg = dict(cfg)
    init_cfg["database"] = None
    conn = pymysql.connect(**init_cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()

    # 连到目标库建表
    with _get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id VARCHAR(64) PRIMARY KEY,
                    openid VARCHAR(64) NOT NULL DEFAULT '',
                    category VARCHAR(32) NOT NULL DEFAULT '',
                    color VARCHAR(32) NOT NULL DEFAULT '',
                    season VARCHAR(32) NOT NULL DEFAULT '四季',
                    material VARCHAR(64) NOT NULL DEFAULT '',
                    style VARCHAR(64) NOT NULL DEFAULT '',
                    fit VARCHAR(64) NOT NULL DEFAULT '',
                    pattern VARCHAR(64) NOT NULL DEFAULT '',
                    brand VARCHAR(128) NOT NULL DEFAULT '',
                    has_logo TINYINT(1) NOT NULL DEFAULT 0,
                    image_url VARCHAR(512) NOT NULL DEFAULT '',
                    image_path VARCHAR(512) NOT NULL DEFAULT '',
                    transparent TINYINT(1) NOT NULL DEFAULT 0,
                    segment_method VARCHAR(64) NOT NULL DEFAULT '',
                    source_photo VARCHAR(512) NOT NULL DEFAULT '',
                    created_at BIGINT NOT NULL DEFAULT 0,
                    INDEX idx_openid (openid),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS photos (
                    id VARCHAR(64) PRIMARY KEY,
                    openid VARCHAR(64) NOT NULL DEFAULT '',
                    url VARCHAR(512) NOT NULL DEFAULT '',
                    created_at BIGINT NOT NULL DEFAULT 0,
                    INDEX idx_openid (openid),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS outfits (
                    date VARCHAR(32) PRIMARY KEY,
                    openid VARCHAR(64) NOT NULL DEFAULT '',
                    items_json MEDIUMTEXT NOT NULL,
                    note VARCHAR(512) NOT NULL DEFAULT '',
                    updated_at BIGINT NOT NULL DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_photo (
                    openid VARCHAR(64) PRIMARY KEY,
                    url VARCHAR(512) NOT NULL DEFAULT '',
                    path VARCHAR(512) NOT NULL DEFAULT '',
                    created_at BIGINT NOT NULL DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tryon_records (
                    id VARCHAR(64) PRIMARY KEY,
                    openid VARCHAR(64) NOT NULL DEFAULT '',
                    item_ids_json MEDIUMTEXT NOT NULL,
                    items_json MEDIUMTEXT NOT NULL,
                    result_url VARCHAR(512) NOT NULL DEFAULT '',
                    image_path VARCHAR(512) NOT NULL DEFAULT '',
                    created_at BIGINT NOT NULL DEFAULT 0,
                    INDEX idx_openid (openid),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    openid VARCHAR(64) PRIMARY KEY,
                    nickname VARCHAR(128) NOT NULL DEFAULT '',
                    avatar VARCHAR(512) NOT NULL DEFAULT '',
                    created_at BIGINT NOT NULL DEFAULT 0,
                    updated_at BIGINT NOT NULL DEFAULT 0,
                    INDEX idx_updated (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            # 兼容：为已存在的旧表补齐 openid 列（新部署的库建表时已包含，这里幂等）
            _ensure_openid_column(cur, "items")
            _ensure_openid_column(cur, "photos")
            _ensure_openid_column(cur, "outfits")
            _ensure_openid_column(cur, "tryon_records")
            # user_photo 是单行用户表：若是旧库建表时可能尚未带 openid 列，补列（允许 NULL 避免旧数据冲突）
            _ensure_openid_column(cur, "user_photo", not_null=False)
        c.commit()
    logger.info("MySQL 数据库初始化完成（database=%s）", db_name)


# 兼容旧调用：确保 PATHS 引用不报错（部分模块可能仍 import）
class _Paths:
    ROOT = str(config.ROOT)
    UPLOADS = str(config.ROOT / "uploads")
    ITEMS = str(config.ROOT / "items")
    DATA = str(config.ROOT / "data")
    TRYON_RESULTS = str(config.ROOT / "tryon_results")


PATHS = _Paths()


# ---------------- 用户（微信授权） ----------------

def get_user(openid: str) -> dict | None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE openid=%s", (openid,))
            row = cur.fetchone()
    if not row:
        return None
    return {
        "openid": row["openid"],
        "nickname": row.get("nickname") or "",
        "avatar": row.get("avatar") or "",
        "createdAt": int(row.get("created_at", 0) or 0),
        "updatedAt": int(row.get("updated_at", 0) or 0),
    }


def upsert_user(openid: str, nickname: str = "", avatar: str = "") -> dict:
    now = int(time.time())
    existing = get_user(openid)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if existing:
                # 仅在传入非空时覆盖昵称/头像，避免清空
                nick = nickname if nickname else existing["nickname"]
                av = avatar if avatar else existing["avatar"]
                cur.execute(
                    "UPDATE users SET nickname=%s, avatar=%s, updated_at=%s "
                    "WHERE openid=%s",
                    (nick, av, now, openid),
                )
            else:
                cur.execute(
                    "INSERT INTO users (openid, nickname, avatar, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (openid, nickname or "", avatar or "", now, now),
                )
        conn.commit()
    return get_user(openid)
