"""衣橱单品表 items 的读写。"""
import os
from pathlib import Path

from store import db, normalize
import config


def _row_to_item(row: dict) -> dict:
    """将数据库行转换为 API 规范 dict（JSON 字段解析）。"""
    item = {
        "id": row["id"],
        "openid": row.get("openid") or "",
        "category": row.get("category") or "",
        "color": row.get("color") or "",
        "season": row.get("season") or "四季",
        "material": row.get("material") or "",
        "style": row.get("style") or "",
        "fit": row.get("fit") or "",
        "pattern": row.get("pattern") or "",
        "name": row.get("name") or "",
        "imageUrl": row.get("image_url") or "",
        "imagePath": row.get("image_path") or "",
        "transparent": bool(row.get("transparent")),
        "segmentMethod": row.get("segment_method") or "",
        "sourcePhoto": row.get("source_photo") or "",
        "createdAt": int(row.get("created_at", 0) or 0),
    }
    return normalize.normalize_item_for_api(item)


def get_items(openid: str = "") -> list:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM items WHERE openid=%s ORDER BY created_at DESC", (openid,))
            else:
                cur.execute("SELECT * FROM items ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [_row_to_item(r) for r in rows]


def get_item(item_id: str, openid: str = ""):
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM items WHERE id=%s AND openid=%s", (item_id, openid))
            else:
                cur.execute("SELECT * FROM items WHERE id=%s", (item_id,))
        row = cur.fetchone()
    if not row:
        return None
    return _row_to_item(row)


def get_items_by_ids(ids: list[str], openid: str = "") -> list:
    """按 id 列表批量查询单品（IN 查询），避免全表拉取后再过滤。"""
    ids = [i for i in (ids or []) if i]
    if not ids:
        return []
    placeholders = ", ".join(["%s"] * len(ids))
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute(
                    f"SELECT * FROM items WHERE id IN ({placeholders}) AND openid=%s",
                    (*ids, openid),
                )
            else:
                cur.execute(
                    f"SELECT * FROM items WHERE id IN ({placeholders})",
                    tuple(ids),
                )
            rows = cur.fetchall()
    return [_row_to_item(r) for r in rows]


def add_items(items: list, openid: str = "") -> None:
    if not items:
        return
    cols = (
        "id", "openid", "category", "color", "season", "material", "style", "fit",
        "pattern", "name", "image_url", "image_path",
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
    with db.get_conn() as conn:
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
                    it.get("name", ""),
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
    with db.get_conn() as conn:
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
    with db.get_conn() as conn:
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
