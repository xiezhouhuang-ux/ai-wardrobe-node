"""
图像分割 / 抠图模块。

仅使用 DashScope 多模态（Qwen 图像编辑）接口把单品从原图抠出，不做本地 rembg / GrabCut 等其他分割方式。
- DEMO 模式（无 API Key）无法调用在线接口，直接落盘原图并返回 transparent=false。
"""
import base64
import io
import logging
import time as _time
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


def segment_with_qwen_image(image_bytes: bytes, meta: dict | None = None) -> str:
    """调用 DashScope 多模态（Qwen 图像编辑）接口，把 meta 描述的单品从原图中抠出。

    仅返回 Qwen 返回的 OSS 临时图片地址（供前端预览），不在本阶段落盘。
    图片落地由 /api/commit 阶段统一下载保存。
    """
    if not API_KEY:
        raise RuntimeError("缺少 QWEN_API_KEY，无法调用 DashScope 多模态接口")

    meta = meta or {}
    prompt = build_segment_prompt(meta)
    img_size = len(image_bytes)
    logger.info("DashScope 分割请求: 图片 %.1f KB, 单品=%s/%s, 提示词=%s",
                img_size / 1024, meta.get("category"), meta.get("color"), prompt)

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
            "size": "768*1152",
            "watermark": False,
        },
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    t0 = _time.time()
    resp = requests.post(IMAGE_ENDPOINT, headers=headers, json=payload, timeout=180)
    elapsed = _time.time() - t0
    logger.info("DashScope 分割 API 返回 status=%s, 耗时 %.1f 秒", resp.status_code, elapsed)

    if resp.status_code != 200:
        err_body = resp.text[:1000] if resp.text else "空响应"
        logger.error("DashScope 分割请求失败 (status=%s), body=%s", resp.status_code, err_body)
        resp.raise_for_status()

    try:
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.error("DashScope 分割响应解析 JSON 失败: %s, body=%s", e, resp.text[:1000])
        raise RuntimeError(f"DashScope 分割响应解析失败: {e}")
    if not isinstance(data, dict):
        # 接口可能返回 null / 非对象结构，避免 'NoneType' object has no attribute 'get'
        logger.error("DashScope 分割响应非预期结构: %s", str(data)[:1000])
        raise RuntimeError(f"DashScope 分割返回非预期结构: {data}")
    logger.info("DashScope 分割原始响应 (截断): %s", str(data)[:2000])

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
    # 直接返回 Qwen OSS 临时地址，供前端预览
    return url


def download_to_local(oss_url: str, out_path: str) -> None:
    """下载 Qwen OSS 临时图片并规整为白底 PNG 写入本地 out_path（入库阶段调用）。"""
    from urllib.parse import urlparse, quote, unquote

    # 确保 URL 格式正确（处理可能的编码问题）
    try:
        parsed = urlparse(oss_url)
        # 对路径中的非 ASCII 字符做编码
        safe_path = quote(unquote(parsed.path), safe="/:@!$&'()*+,;=")
        url = parsed._replace(path=safe_path).geturl()
    except Exception:
        url = oss_url

    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AI-Wardrobe/1.0)",
    }, timeout=120)
    resp.raise_for_status()

    if not resp.content:
        raise RuntimeError("OSS 返回空内容，图片可能已过期")

    png = normalize_to_png(resp.content)
    Path(out_path).write_bytes(png)
    logger.info("已下载分割结果图 -> %s (%d bytes)", out_path, len(png))


def extract_item(src_path: str, meta: dict) -> dict:
    """
    根据原图 src_path 与识别信息 meta，调用 DashScope 多模态接口得到分割结果。

    本阶段仅返回 Qwen OSS 临时图片地址（imageUrl）供前端预览，不落盘。
    本地落地在 /api/commit 阶段通过 download_to_local 完成。
    """
    original = Path(src_path).read_bytes()

    if not DEMO_MODE:
        try:
            oss_url = segment_with_qwen_image(original, meta)
            return {
                "imageUrl": oss_url,
                "imagePath": "",
                "transparent": False,
                "segmentMethod": "dashscope",
                "sourcePhoto": src_path,
            }
        except Exception as e:
            logger.warning("DashScope 分割失败：%s", e)
            raise

    # demo 模式：无 API Key，无法调用在线分割，返回原图本地地址
    return {
        "imageUrl": "/uploads/photos/" + Path(src_path).name,
        "imagePath": str(src_path),
        "transparent": False,
        "segmentMethod": "original",
    }
