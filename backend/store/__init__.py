"""MySQL 存储模块（按业务模块分目录）。

对外统一通过 ``import store`` 访问（本包在 __init__ 中重新导出各子模块
的公开函数），保持历史调用方无需改动。

数据库表结构：
  - items         衣橱单品
  - photos        上传的原始照片
  - outfits       日历穿搭
  - user_photo    用户全身照（单行）
  - tryon_records 试穿记录
  - users         微信授权用户
"""
import logging
import os
import threading

import pymysql
from pymysql.cursors import DictCursor

import config
from config import MYSQL_CONFIG

from store import (
    db as _db,
    normalize as _normalize,
    items as _items,
    photos as _photos,
    outfits as _outfits,
    user_photo as _user_photo,
    tryon as _tryon,
    admin as _admin,
)

logger = logging.getLogger("store")

# 连接与初始化
_get_conn = _db.get_conn
init_db = _db.init_db

# 数据规范化
normalize_item_for_api = _normalize.normalize_item_for_api

# 衣橱单品
get_items = _items.get_items
get_item = _items.get_item
add_items = _items.add_items
delete_item = _items.delete_item
get_stats = _items.get_stats

# 原始照片
add_photo = _photos.add_photo
get_photos = _photos.get_photos

# 日历穿搭
get_outfits = _outfits.get_outfits
get_outfit = _outfits.get_outfit
save_outfit = _outfits.save_outfit
delete_outfit = _outfits.delete_outfit

# 用户全身照 + 微信用户
get_user_photo = _user_photo.get_user_photo
save_user_photo = _user_photo.save_user_photo
get_user = _user_photo.get_user
upsert_user = _user_photo.upsert_user

# 试穿记录
get_tryon_records = _tryon.get_tryon_records
save_tryon_record = _tryon.save_tryon_record
delete_tryon_record = _tryon.delete_tryon_record

# 后台管理（跨用户全量）
get_admin_stats = _admin.get_admin_stats
list_all_items = _admin.list_all_items
list_all_tryon = _admin.list_all_tryon
list_all_outfits = _admin.list_all_outfits


# 兼容旧调用：确保 PATHS 引用不报错（部分模块可能仍 import）
class _Paths:
    ROOT = str(config.ROOT)
    UPLOADS = str(config.ROOT / "uploads")
    ITEMS = str(config.ROOT / "items")
    DATA = str(config.ROOT / "data")
    TRYON_RESULTS = str(config.ROOT / "tryon_results")


PATHS = _Paths()
