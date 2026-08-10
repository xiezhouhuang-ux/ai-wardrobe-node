"""日历穿搭表 outfits 的读写。"""
import json


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


def get_outfits(openid: str = "") -> list:
    from store import db
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM outfits WHERE openid=%s ORDER BY date DESC", (openid,))
            else:
                cur.execute("SELECT * FROM outfits ORDER BY date DESC")
            rows = cur.fetchall()
    return [_row_to_outfit(r) for r in rows]


def get_outfit(date: str, openid: str = ""):
    from store import db
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("SELECT * FROM outfits WHERE date=%s AND openid=%s", (date, openid))
            else:
                cur.execute("SELECT * FROM outfits WHERE date=%s", (date,))
            row = cur.fetchone()
    return _row_to_outfit(row) if row else None


def save_outfit(outfit: dict) -> dict:
    from store import db
    date = outfit.get("date")
    openid = outfit.get("openid", "")
    items_json = json.dumps(outfit.get("items", []), ensure_ascii=False)
    note = outfit.get("note", "")
    updated_at = int(outfit.get("updatedAt", 0) or 0)
    with db.get_conn() as conn:
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
    from store import db
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if openid:
                cur.execute("DELETE FROM outfits WHERE date=%s AND openid=%s", (date, openid))
            else:
                cur.execute("DELETE FROM outfits WHERE date=%s", (date,))
            affected = cur.rowcount
        conn.commit()
    return bool(affected)
