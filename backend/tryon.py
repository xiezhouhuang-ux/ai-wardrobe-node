"""
AI 虚拟试穿模块。

利用 DashScope 多模态图像生成接口，将衣橱单品「穿」到用户的全身照上，
生成试穿效果预览图。
"""
import base64
import io
import logging
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from config import API_KEY, IMAGE_ENDPOINT, IMAGE_MODEL

logger = logging.getLogger("tryon")

# 试穿专用模型（如果后续需要独立配置可改）
TRYON_MODEL = IMAGE_MODEL  # qwen-image-2.0-pro


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _image_to_data_url(path: str) -> str:
    """将本地图片文件读取为 base64 data URL。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"图片不存在: {path}")
    data = p.read_bytes()
    # 推断 MIME 类型
    suffix = p.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    mime = mime_map.get(suffix, "image/png")
    return f"data:{mime};base64,{_b64(data)}"


def _image_bytes_to_data_url(image_bytes: bytes, size: int = 1024) -> str:
    """压缩并转换为 data URL，限制最长边不超过 size 像素以控制请求体积。"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > size:
            ratio = size / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return f"data:image/jpeg;base64,{_b64(buf.getvalue())}"
    except Exception:
        # 无法用 Pillow 处理则原样返回
        return f"data:image/png;base64,{_b64(image_bytes)}"


def build_tryon_prompt(items_desc: list) -> str:
    """根据选定单品描述生成试穿提示词。"""
    parts = []
    for it in items_desc:
        cat = it.get("category", "")
        color = it.get("color", "")
        style = it.get("style", "")
        parts.append(f"{color}{style}{cat}")
    item_str = "、".join(parts)
    return (
        f"虚拟试穿任务：第一张图是人物的全身正面照，第二张图是按顺序自上而下排列的待换穿搭单品（{item_str}）。\n"
        "请将人物身上的服装替换为第二张图中的对应单品。\n"
        "硬性要求：\n"
        "1. 严格保持人物的面部特征、姿势、体型、背景不变。\n"
        "2. 仅替换服装的款式和颜色，不要改变人体的其他部分。\n"
        "3. 服装需自然贴合身体，与原图光照/角度协调。\n"
        "4. 输出图片宽高比与原人物照一致。\n"
        "5. 不要输出第二张拼图中的单品本身，只输出人物换装后的全身图。"
    )


def virtual_tryon(
    person_photo: bytes,     # 用户全身照的原始字节
    item_images: list,       # [{imageUrl: str, category: str, color: str, style: str}, ...]
    timeout: int = 180,
) -> str:
    """
    调用 Qwen 图像生成模型进行虚拟试穿，返回生成图片的 OSS 临时 URL。

    参数：
        person_photo: 用户全身照的 bytes
        item_images: 衣橱单品列表，每个元素需包含 imageUrl（本地绝对路径或 /items/ 路径）和属性
        timeout: 请求超时秒数

    返回：
        OSS 临时图片 URL（24 小时有效）
    """
    if not API_KEY:
        raise RuntimeError("缺少 QWEN_API_KEY，无法调用试穿模型。请设置环境变量。")

    # 压缩用户照片
    person_b64 = _image_bytes_to_data_url(person_photo)

    # 将所有单品合并为一张拼图（Qwen 图像编辑接口最多 1-3 张图：1 张人 + 1 张服饰拼图 + 1 张可选）
    from PIL import Image as PILImage
    import io as _io

    valid_items = []
    for it in item_images:
        img_path: Any = it.get("imagePath", "")
        if not Path(img_path).exists():
            logger.warning("单品图片不存在，跳过: %s", img_path)
            continue
        valid_items.append((img_path, it))

    if not valid_items:
        raise RuntimeError("没有有效的单品图片可用于试穿")

    # 按分类标签把单品组成拼图
    cell_size = 256
    n = len(valid_items)
    grid_w = cell_size
    grid_h = cell_size * n
    canvas = PILImage.new("RGB", (grid_w, grid_h), (255, 255, 255))
    for idx, (img_path, it) in enumerate(valid_items):
        try:
            im = PILImage.open(img_path).convert("RGBA")
            # 透明底换白底
            bg = PILImage.new("RGBA", im.size, (255, 255, 255, 255))
            im = PILImage.alpha_composite(bg, im).convert("RGB")
            im.thumbnail((cell_size, cell_size), PILImage.LANCZOS)
            x = (cell_size - im.width) // 2
            y = idx * cell_size + (cell_size - im.height) // 2
            canvas.paste(im, (x, y))
        except Exception as e:
            logger.warning("无法加载单品图 %s: %s", img_path, e)
    # 压缩拼图
    buf = _io.BytesIO()
    canvas.save(buf, format="JPEG", quality=85)
    collage_b64 = f"data:image/jpeg;base64,{_b64(buf.getvalue())}"

    item_descs = [
        {"category": it.get("category", ""), "color": it.get("color", ""), "style": it.get("style", "")}
        for _, it in valid_items
    ]

    # 构建 content：人物照 + 服饰拼图 + 文字
    content = [
        {"image": person_b64},
        {"image": collage_b64},
    ]

    if not item_descs:
        raise RuntimeError("没有有效的单品图片可用于试穿")

    prompt = build_tryon_prompt(item_descs)
    content.append({"text": prompt})

    payload = {
        "model": TRYON_MODEL,
        "input": {
            "messages": [
                {"role": "user", "content": content}
            ]
        },
        "parameters": {"n": 1, "size": "768*1152", "watermark": False},
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    logger.info("试穿请求: %d 件单品, 拼图尺寸 %dx%d", len(valid_items), grid_w, grid_h)
    t0 = time.time()
    resp = requests.post(IMAGE_ENDPOINT, headers=headers, json=payload, timeout=timeout)
    elapsed = time.time() - t0
    logger.info("试穿 API 返回 status=%s, 耗时 %.1f 秒", resp.status_code, elapsed)

    if resp.status_code != 200:
        err = resp.text[:2000] if resp.text else "未知错误"
        logger.error("试穿 API 请求失败 (status=%s), body=%s", resp.status_code, err)
        raise RuntimeError(f"试穿 API 返回 {resp.status_code}: {err}")

    data = resp.json()
    logger.info("试穿 API 原始响应 (截断): %s", str(data)[:2000])

    url = _extract_result_url(data)
    if not url:
        err_msg = data.get("message") or data.get("code") or "未知错误"
        raise RuntimeError(f"试穿生成失败: {err_msg}")

    return url


def _extract_result_url(data: dict) -> str:
    """从 Qwen 多模态生成响应中提取结果图片 URL。"""
    output = data.get("output") or {}
    choices = output.get("choices") or []
    if not choices:
        # 某些情况图片直接在 output.image 下
        img = output.get("image")
        if isinstance(img, str):
            return img
        return ""

    for choice in choices:
        if isinstance(choice, dict):
            msg = choice.get("message", {})
            content = msg.get("content") or []
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("image"):
                        return item["image"]
            # fallback
            img = choice.get("image", {})
            url = img.get("url") if isinstance(img, dict) else (img if isinstance(img, str) else None)
            if url:
                return url

    return ""


def download_to_local(oss_url: str, out_path: str) -> None:
    """从 OSS 临时 URL 下载试穿结果图片到本地。"""
    from segment import normalize_to_png

    logger.info("下载试穿结果: %s -> %s", oss_url, out_path)
    resp = requests.get(oss_url, timeout=60)
    resp.raise_for_status()
    normalized = normalize_to_png(resp.content)
    Path(out_path).write_bytes(normalized)
    logger.info("试穿结果已保存到 %s", out_path)
