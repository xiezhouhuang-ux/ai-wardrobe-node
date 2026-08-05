"""
Qwen VL 服装识别模块。复刻原 lib/qwen.js 的 detectClothing + extractJson + normalize + dedup。
"""
import base64
import json
import logging
import os
import re
import time
from pathlib import Path

import requests

from config import API_KEY, DEMO_MODE, QWEN_MODEL, VISION_BASE_URL
from prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger("qwen")

# 受控英文词表（用于校正模型输出）
CATEGORY_VOCAB = {"Top", "Bottom", "Shoes", "Bag"}
CATEGORY_LABEL_ZH = {"Top": "上衣", "Bottom": "下装", "Shoes": "鞋", "Bag": "包"}

# 英文颜色 -> 中文颜色（覆盖常见模型输出）
COLOR_MAP_ZH = {
    "black": "黑", "white": "白", "gray": "灰", "grey": "灰", "beige": "米",
    "khaki": "卡其", "blue": "蓝", "navy": "藏蓝", "denim": "牛仔蓝", "red": "红",
    "green": "绿", "brown": "棕", "pink": "粉", "purple": "紫", "yellow": "黄",
    "orange": "橙", "cream": "米", "camel": "驼", "wine": "酒红", "maroon": "酒红",
    "olive": "橄榄绿", "mint": "薄荷绿", "skyblue": "天蓝", "lightblue": "浅蓝",
    "silver": "银", "gold": "金",
}

# 常见品牌（用于把英文品牌映射到中文/原样）
KNOWN_BRANDS = {
    "nike": "Nike", "adidas": "Adidas", "uniqlo": "优衣库", "zara": "Zara",
    "hm": "H&M", "gucci": "Gucci", "chanel": "Chanel", "lv": "Louis Vuitton",
    "louisvuitton": "Louis Vuitton", "prada": "Prada", "supreme": "Supreme",
    "newbalance": "New Balance", "converse": "Converse", "vans": "Vans",
    "nba": "NBA", "champion": "Champion", "fila": "Fila", "puma": "Puma",
    "lacoste": "Lacoste", "ralphlauren": "Ralph Lauren", "tommy": "Tommy Hilfiger",
    "ck": "Calvin Klein", "calvinklein": "Calvin Klein", "bosideng": "波司登",
    "li ning": "李宁", "lining": "李宁", "anta": "安踏", "erke": "鸿星尔克",
}

SEASON_VOCAB = {"春", "夏", "秋", "冬", "四季"}


def _media_type(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mapping = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp",
    }
    return mapping.get(ext, "image/jpeg")


def _extract_json(text: str):
    if text is None:
        return []
    s = text.strip()
    # 去掉 ```json ... ``` 代码块
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
        s = s.strip()
    # 截取首个 [ ... ] 片段
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    try:
        data = json.loads(s)
    except Exception:
        return []
    if isinstance(data, dict):
        data = data.get("items", [])
    if not isinstance(data, list):
        return []
    return data


def _norm_category(cat: str) -> str:
    if not cat:
        return "Top"
    c = str(cat).strip().lower()
    # 直接命中
    for v in CATEGORY_VOCAB:
        if v.lower() == c:
            return v
    # 关键词兜底
    if any(k in c for k in ("top", "shirt", "tee", "上衣", "外套", "卫衣", "t恤", "衫")):
        return "Top"
    if any(k in c for k in ("bottom", "pant", "trouser", "skirt", "下装", "裤", "裙")):
        return "Bottom"
    if any(k in c for k in ("shoe", "sneaker", "boot", "鞋")):
        return "Shoes"
    if any(k in c for k in ("bag", "backpack", "包", "背包")):
        return "Bag"
    return "Top"


def _norm_color(color) -> str:
    if not color:
        return "未知"
    c = str(color).strip().lower()
    if c in COLOR_MAP_ZH:
        return COLOR_MAP_ZH[c]
    # 已经是中文则原样保留
    if re.search(r"[一-龥]", c):
        return str(color).strip()
    # 未知英文统一为“其他”
    return "其他"


def _norm_brand(brand) -> str:
    if not brand:
        return ""
    b = str(brand).strip()
    if re.search(r"[一-龥]", b):
        return b
    key = b.lower().replace(" ", "")
    if key in KNOWN_BRANDS:
        return KNOWN_BRANDS[key]
    # 形如 “Nike” 直接保留；纯英文小写尝试首字母大写
    if re.fullmatch(r"[a-zA-Z0-9 &.'/+-]+", b):
        return b
    return ""


def _norm_season(season) -> str:
    if not season:
        return "四季"
    s = str(season).strip()
    for v in SEASON_VOCAB:
        if v in s:
            return v
    return "四季"


def normalize(raw: dict) -> dict:
    cat_en = _norm_category(raw.get("category"))
    cat_zh = CATEGORY_LABEL_ZH.get(cat_en, cat_en)
    return {
        "category": cat_zh,
        "color": _norm_color(raw.get("color")),
        "season": _norm_season(raw.get("season")),
        "material": str(raw.get("material") or "未知").strip() or "未知",
        "style": str(raw.get("style") or "休闲").strip() or "休闲",
        "fit": str(raw.get("fit") or "常规").strip() or "常规",
        "pattern": str(raw.get("pattern") or "纯色").strip() or "纯色",
        "brand": _norm_brand(raw.get("brand")),
        "hasLogo": bool(raw.get("hasLogo", False)),
    }


def dedup(items: list) -> list:
    seen = set()
    out = []
    for it in items:
        key = (it["category"], it["color"])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def detect_clothing(image_path: str) -> list:
    """识别单张图片中的所有服装单品，返回规范化后的 dict 列表。"""
    if DEMO_MODE:
        return []

    with open(image_path, "rb") as f:
        raw_data = f.read()
        b64 = base64.b64encode(raw_data).decode("ascii")

    img_size = len(raw_data)
    logger.info("开始 VL 分析图片: %s (%.1f KB)", image_path, img_size / 1024)

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(_media_type(image_path), b64)},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    url = VISION_BASE_URL.rstrip("/") + "/chat/completions"

    t0 = time.time()
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    elapsed = time.time() - t0
    logger.info("VL API 返回 status=%s, 耗时 %.1f 秒", resp.status_code, elapsed)

    if resp.status_code != 200:
        err_body = resp.text[:1000] if resp.text else "空响应"
        logger.error("VL API 请求失败 (status=%s), body=%s", resp.status_code, err_body)
        resp.raise_for_status()

    data = resp.json()
    logger.info("VL API 原始响应: %s", str(data)[:2000])
    content = data["choices"][0]["message"]["content"]
    logger.info("VL 返回内容: %s", content[:1000])
    raw_list = _extract_json(content)
    norm = [normalize(r) for r in raw_list]
    result = dedup(norm)
    logger.info("VL 识别结果: %d 个单品 (原始 %d 个)", len(result), len(raw_list))
    return result
