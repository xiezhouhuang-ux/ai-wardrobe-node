"""
配置模块。从环境变量读取配置（行为与原 Node 版 env.js 一致：
不覆盖已存在的环境变量）。无 API Key 时自动进入 demo 模式。
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent

# 加载仓库根目录的 .env（不覆盖已存在的环境变量），与 Node 版 .env.config({ override: false }) 一致
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=ROOT / ".env", override=False)
except Exception:
    pass

API_KEY = (os.getenv("QWEN_API_KEY") or "").strip()

VISION_BASE_URL = os.getenv("QWEN_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
IMAGE_ENDPOINT = (
    os.getenv("QWEN_IMAGE_ENDPOINT")
    or "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
)

QWEN_MODEL = os.getenv("QWEN_MODEL") or "qwen2.5-vl-72b-instruct"
IMAGE_MODEL = os.getenv("QWEN_IMAGE_MODEL") or "qwen-image-2.0-pro"

# 没有 API Key -> demo 模式（不调用真实模型）
DEMO_MODE = not API_KEY

# 是否启用离线抠图（rembg）；未显式关闭则默认开启
ENABLE_CUTOUT = os.getenv("ENABLE_CUTOUT", "1") != "0"

PORT = int(os.getenv("PORT", "8000"))

PATHS = {
    "ROOT": str(ROOT),
    "UPLOADS": str(ROOT / "uploads"),
    "ITEMS": str(ROOT / "items"),
    "DATA": str(ROOT / "data"),
    "WARDROBE_DB": str(ROOT / "data" / "wardrobe.json"),
    "TRYON_RESULTS": str(ROOT / "tryon_results"),
}


def ensure_dirs() -> None:
    for key in ("UPLOADS", "ITEMS", "DATA", "TRYON_RESULTS"):
        os.makedirs(PATHS[key], exist_ok=True)
