"""原始照片表 photos 的读写（uploads 历史上传）。"""


def add_photo(photo: dict, openid: str = "") -> None:
    from store import db
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO photos (id, openid, url, created_at) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE openid=VALUES(openid), url=VALUES(url), created_at=VALUES(created_at)",
                (photo.get("id"), openid, photo.get("url"), int(photo.get("createdAt", 0) or 0)),
            )
        conn.commit()


def get_photos(openid: str = "") -> list:
    from store import db
    with db.get_conn() as conn:
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
