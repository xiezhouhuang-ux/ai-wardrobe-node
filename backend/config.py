"""
配置模块。从环境变量读取配置（行为与原 Node 版 env.js 一致：
不覆盖已存在的环境变量）。无 API Key 时自动进入 demo 模式。
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR  # 所有资源文件统一放在 backend 目录下

# 加载 backend 目录下的 .env（不覆盖已存在的环境变量）
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

# ---------------- 微信小程序内容安全（对外发布场景必接） ----------------
# 填了 AppID + Secret 才会真正调用微信 msgSecCheck / imgSecCheck；
# 未填则自动降级为放行（DEMO / 本地调试用），不会阻断流程。
WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")
# 内容安全总开关：0 关闭（全部放行），默认开启
CONTENT_SECURITY_ENABLED = os.getenv("CONTENT_SECURITY_ENABLED", "1") != "0"

PORT = int(os.getenv("PORT", "8000"))

# ---------------- MySQL 配置 ----------------
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ai_wardrobe")

# 兼容旧代码引用：保留 ROOT 派生目录常量
UPLOADS = str(ROOT / "uploads")
ITEMS = str(ROOT / "items")
DATA = str(ROOT / "data")
TRYON_RESULTS = str(ROOT / "tryon_results")

MYSQL_CONFIG = {
    "host": MYSQL_HOST,
    "port": MYSQL_PORT,
    "user": MYSQL_USER,
    "password": MYSQL_PASSWORD,
    "database": MYSQL_DATABASE,
    "charset": "utf8mb4",
    "autocommit": False,
    "connect_timeout": 10,
}


def ensure_dirs() -> None:
    # 保留原有目录（上传/分割/试穿结果图仍然存本地文件系统）
    for d in (ROOT / "uploads", ROOT / "items", ROOT / "data", ROOT / "tryon_results"):
        os.makedirs(str(d), exist_ok=True)
