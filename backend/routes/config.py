"""配置类接口：能力开关（DEBUG 模式、抠图开关、模型名等）。"""
from fastapi import APIRouter

from config import DEMO_MODE, ENABLE_CUTOUT, QWEN_MODEL, IMAGE_MODEL

router = APIRouter(tags=["config"])


@router.get("/api/config")
def api_config():
    return {
        "demo": DEMO_MODE,
        "enableCutout": ENABLE_CUTOUT,
        "qwenModel": QWEN_MODEL,
        "imageModel": IMAGE_MODEL,
    }
