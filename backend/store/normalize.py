"""单品数据规范化：将数据库中的中英混排字段统一为前端展示的中文。"""
import time

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
        it["id"] = f"it_{int(time.time() * 1000)}"
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
    return it
