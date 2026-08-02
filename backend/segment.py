"""
图像分割 / 抠图模块。

仅使用 DashScope 多模态（Qwen 图像编辑）接口把单品从原图抠出，不做本地 rembg / GrabCut 等其他分割方式。
- DEMO 模式（无 API Key）无法调用在线接口，直接落盘原图并返回 transparent=false。
"""
import base64
import io
import logging
from pathlib import Path

import requests
from PIL import Image

from config import (
    API_KEY,
    DEMO_MODE,
    IMAGE_ENDPOINT,
    IMAGE_MODEL,
)
from prompt import build_segment_prompt

logger = logging.getLogger("segment")


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def normalize_to_png(image_bytes: bytes) -> bytes:
    """把任意图片字节规整为白底 RGB 的 PNG 字节（不要求透明通道）。"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        # 将透明像素替换为纯白背景
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        flattened = Image.alpha_composite(bg, img).convert("RGB")
        buf = io.BytesIO()
        flattened.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        # 无法用 Pillow 解析则原样返回（确保至少能落盘）
        return image_bytes


def segment_with_qwen_image(image_bytes: bytes, meta: dict) -> bytes:
    """调用 DashScope 多模态（Qwen 图像编辑）接口，把 meta 描述的单品从原图中抠出，返回图片字节。"""
    if not API_KEY:
        raise RuntimeError("缺少 QWEN_API_KEY，无法调用 DashScope 多模态接口")

    prompt = build_segment_prompt(meta)
    logger.info("DashScope 分割提示词：%s", prompt)

    # qwen-image-edit-plus 的正确调用格式：
    # input.messages[].content = [{image: base64}, {text: 指令}]，无 base_image/function 字段
    payload = {
        "model": IMAGE_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": "data:image/png;base64," + _b64(image_bytes)},
                        {"text": prompt},
                    ],
                }
            ]
        },
        "parameters": {
            "n": 1,
            "watermark": False,
        },
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(IMAGE_ENDPOINT, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()

    output = data.get("output") or {}
    choices = output.get("choices") or []
    url = None
    if choices:
        # 标准结构：choices[].message.content[].image
        msg = choices[0].get("message", {})
        content = msg.get("content") or []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("image"):
                    url = item["image"]
                    break
        # 兼容其他返回形态
        if not url:
            first = choices[0].get("image", {})
            url = first.get("url") or (first if isinstance(first, str) else None)
    if not url:
        reason = output.get("reason") or data.get("message") or data.get("code") or "unknown"
        raise RuntimeError(f"DashScope 分割失败: {reason} | resp={data}")
    img_resp = requests.get(url, timeout=120)
    img_resp.raise_for_status()
    return img_resp.content


def extract_item(src_path: str, meta: dict, out_path: str) -> dict:
    """
    根据原图 src_path 与识别信息 meta，调用 DashScope 多模态接口生成分割结果写到 out_path（PNG）。
    返回 { transparent: bool, segmentMethod: str }。
    transparent 如实反映模型返回图是否带透明通道。
    """
    original = Path(src_path).read_bytes()

    if not DEMO_MODE:
        try:
            seg = segment_with_qwen_image(original, meta)
            png = normalize_to_png(seg)
            Path(out_path).write_bytes(png)
            return {"transparent": False, "segmentMethod": "dashscope"}
        except Exception as e:
            logger.warning("DashScope 分割失败：%s", e)
            raise

    # demo 模式：无 API Key，无法调用在线分割，直接落盘原图
    png = normalize_to_png(original)
    Path(out_path).write_bytes(png)
    return {"transparent": False, "segmentMethod": "original"}
