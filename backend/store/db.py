"""数据库连接与数据库初始化（建表、补齐旧表列）。"""
import logging
import threading

import pymysql
from pymysql.cursors import DictCursor

from config import MYSQL_CONFIG

logger = logging.getLogger("store")

_conn_lock = threading.Lock()


def get_conn():
    """获取一个数据库连接（线程安全；每次新建连接并开启 autocommit）。"""
    conn = pymysql.connect(cursorclass=DictCursor, **MYSQL_CONFIG)
    conn.autocommit_mode = True
    return conn


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
    with get_conn() as c:
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
                    name VARCHAR(64) NOT NULL DEFAULT '',
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
            # 兼容旧库：items 表补齐 name 列（新部署建表时已包含，这里幂等）
            try:
                cur.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name='items' AND column_name='name'"
                )
                if not cur.fetchone():
                    cur.execute(
                        "ALTER TABLE items ADD COLUMN name VARCHAR(64) NOT NULL DEFAULT ''"
                    )
            except Exception as e:
                logger.warning("为 items 表补 name 列失败（可忽略）: %s", e)
        c.commit()
    logger.info("MySQL 数据库初始化完成（database=%s）", db_name)
