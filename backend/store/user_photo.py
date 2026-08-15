"""用户全身照表 user_photo 与微信用户表 users 的读写。"""
import random
import time


def get_user_photo(openid: str = "") -> dict | None:
    from store import db
    with db.get_conn() as conn:
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
    from store import db
    openid = photo.get("openid", "")
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # 按 openid upsert
            cur.execute(
                "INSERT INTO user_photo (openid, url, path, created_at) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE url=VALUES(url), path=VALUES(path), created_at=VALUES(created_at)",
                (openid, photo.get("url"), photo.get("path"), int(photo.get("createdAt", 0) or 0)),
            )
        conn.commit()


def get_user(openid: str) -> dict | None:
    from store import db
    with db.get_conn() as conn:
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


def _random_nickname() -> str:
    """首次注册时生成一个随机昵称，例如「衣橱用户8247」。"""
    prefixes = ["衣橱用户", "时尚星", "穿搭控", "随心搭"]
    return f"{random.choice(prefixes)}{random.randint(1000, 9999)}"


def upsert_user(openid: str, nickname: str = "", avatar: str = "") -> dict:
    from store import db
    now = int(time.time())
    existing = get_user(openid)
    with db.get_conn() as conn:
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
                # 首次注册：昵称为空则随机生成，避免「微信用户」千篇一律
                nick = nickname or _random_nickname()
                cur.execute(
                    "INSERT INTO users (openid, nickname, avatar, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (openid, nick, avatar or "", now, now),
                )
        conn.commit()
    return get_user(openid)
