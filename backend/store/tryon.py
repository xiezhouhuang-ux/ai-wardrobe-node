"""试穿记录表 tryon_records 的读写。"""
import json
import os


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


def get_tryon_records(openid: str = "") -> list:
    from store import db
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM tryon_records WHERE openid=%s ORDER BY created_at DESC", (openid,))
            else:
                cur.execute("SELECT * FROM tryon_records ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [_row_to_tryon(r) for r in rows]


def save_tryon_record(record: dict) -> dict:
    from store import db
    openid = record.get("openid", "")
    with db.get_conn() as conn:
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
    from store import db
    # 删除本地结果图
    record = None
    with db.get_conn() as conn:
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
