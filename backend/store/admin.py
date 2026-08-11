"""后台管理：跨用户全量统计与分页查询。"""
from store import db, normalize


def get_admin_stats() -> dict:
    """后台概览统计：用户数、单品数、试穿数、搭配数。"""
    stats = {}
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT openid) AS c FROM items WHERE openid<>''")
            stats["users"] = cur.fetchone().get("c") or 0
            cur.execute("SELECT COUNT(*) AS c FROM items")
            stats["items"] = cur.fetchone().get("c") or 0
            cur.execute("SELECT COUNT(*) AS c FROM tryon_records")
            stats["tryons"] = cur.fetchone().get("c") or 0
            cur.execute("SELECT COUNT(*) AS c FROM outfits")
            stats["outfits"] = cur.fetchone().get("c") or 0
    return stats


def list_all_items(page: int = 1, size: int = 20, keyword: str = "") -> dict:
    """后台：跨用户分页查询单品，支持按名称/品类/颜色关键字搜索。"""
    page = max(1, int(page))
    size = min(100, max(1, int(size)))
    offset = (page - 1) * size
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if keyword:
                like = f"%{keyword}%"
                cur.execute(
                    "SELECT * FROM items WHERE name LIKE %s OR category LIKE %s OR color LIKE %s "
                    "ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (like, like, like, size, offset),
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT COUNT(*) AS c FROM items WHERE name LIKE %s OR category LIKE %s OR color LIKE %s",
                    (like, like, like),
                )
            else:
                cur.execute("SELECT * FROM items ORDER BY created_at DESC LIMIT %s OFFSET %s", (size, offset))
                rows = cur.fetchall()
                cur.execute("SELECT COUNT(*) AS c FROM items")
            row = cur.fetchone() or {"c": 0}
            total = row.get("c") or 0
    return {
        "list": [_row_to_item(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


def _row_to_item(row: dict) -> dict:
    item = {
        "id": row["id"],
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


def list_all_tryon(page: int = 1, size: int = 20) -> dict:
    """后台：跨用户分页查询试穿记录。"""
    page = max(1, int(page))
    size = min(100, max(1, int(size)))
    offset = (page - 1) * size
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tryon_records ORDER BY created_at DESC LIMIT %s OFFSET %s", (size, offset))
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS c FROM tryon_records")
            row = cur.fetchone() or {"c": 0}
            total = row.get("c") or 0
    return {
        "list": [_row_to_tryon(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


def _row_to_tryon(row: dict) -> dict:
    import json
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


def _row_to_outfit(row: dict) -> dict:
    import json
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


def list_all_users(page: int = 1, size: int = 20, keyword: str = "", exclude_openid: str = "") -> dict:
    """后台：分页查询微信授权用户，支持按昵称/openid 关键字搜索。

    exclude_openid 非空时，在 SQL 层直接排除该 openid（用于前端「列出其他用户」场景）。
    """
    page = max(1, int(page))
    size = min(500, max(1, int(size)))
    offset = (page - 1) * size
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if keyword:
                like = f"%{keyword}%"
                sql = "SELECT * FROM users WHERE (nickname LIKE %s OR openid LIKE %s)"
                params = [like, like]
                if exclude_openid:
                    sql += " AND openid != %s"
                    params.append(exclude_openid)
                sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([size, offset])
                cur.execute(sql, params)
                rows = cur.fetchall()
                cnt_sql = "SELECT COUNT(*) AS c FROM users WHERE (nickname LIKE %s OR openid LIKE %s)"
                cnt_params = [like, like]
                if exclude_openid:
                    cnt_sql += " AND openid != %s"
                    cnt_params.append(exclude_openid)
                cur.execute(cnt_sql, cnt_params)
            else:
                if exclude_openid:
                    cur.execute(
                        "SELECT * FROM users WHERE openid != %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                        (exclude_openid, size, offset),
                    )
                    rows = cur.fetchall()
                    cur.execute("SELECT COUNT(*) AS c FROM users WHERE openid != %s", (exclude_openid,))
                else:
                    cur.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s", (size, offset))
                    rows = cur.fetchall()
                    cur.execute("SELECT COUNT(*) AS c FROM users")
            row = cur.fetchone() or {"c": 0}
            total = row.get("c") or 0
    return {
        "list": [_row_to_user(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


def _row_to_user(row: dict) -> dict:
    return {
        "openid": row.get("openid") or "",
        "nickname": row.get("nickname") or "",
        "avatar": row.get("avatar") or "",
        "createdAt": int(row.get("created_at", 0) or 0),
        "updatedAt": int(row.get("updated_at", 0) or 0),
    }


def list_all_outfits(page: int = 1, size: int = 20) -> dict:
    """后台：跨用户分页查询搭配/日历记录。"""
    page = max(1, int(page))
    size = min(100, max(1, int(size)))
    offset = (page - 1) * size
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM outfits ORDER BY updated_at DESC LIMIT %s OFFSET %s", (size, offset))
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS c FROM outfits")
            row = cur.fetchone() or {"c": 0}
            total = row.get("c") or 0
    return {
        "list": [_row_to_outfit(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }
