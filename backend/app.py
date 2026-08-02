"""
AI 数字衣橱 - Python 后端（FastAPI）。

API：
  GET  /api/config            返回 demo 模式、模型、抠图开关
  POST /api/analyze           上传照片 -> 仅用 VL 视觉模型分析候选单品（不分割、不入库）
  POST /api/segment           对确认的单品做分割，返回预览图（不入库）
  POST /api/commit            将确认的单品正式入库
  POST /api/process           （兼容）一步式：识别+抠图+入库
  GET  /api/items             列出全部单品
  GET  /api/items/<id>        获取单个单品
  DELETE /api/items/<id>      删除单品（同时删除实体图片）
  GET  /api/stats             统计

静态：/uploads、/items 由本服务直接提供；生产构建后也会托管 frontend/dist。
"""
import logging
import sys
import time
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 确保无论从哪个工作目录启动都能导入同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from qwen import detect_clothing
from segment import download_to_local, extract_item
from store import add_items, add_photo, delete_item, get_item, get_items, get_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

config.ensure_dirs()

app = FastAPI(title="AI 数字衣橱", version="1.0.0")

# 开发期允许前端 Vite 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_MAX = 20
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def _save_upload(upload: UploadFile) -> Path:
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        ext = ".jpg"
    name = _new_id("u") + ext
    dest = Path(config.PATHS["UPLOADS"]) / name
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    dest.write_bytes(data)
    return dest


@app.get("/api/config")
def api_config():
    return {
        "demoMode": config.DEMO_MODE,
        "visionModel": config.QWEN_MODEL,
        "imageModel": config.IMAGE_MODEL,
        "cutoutEnabled": config.ENABLE_CUTOUT,
    }


@app.post("/api/process")
def api_process(photos: list[UploadFile] = File(..., description="照片文件，字段名 photos")):
    if not photos:
        raise HTTPException(status_code=400, detail="未收到照片")
    photos = photos[:UPLOAD_MAX]

    result = []
    new_items = []
    for upload in photos:
        src = _save_upload(upload)
        photo_url = f"/uploads/{src.name}"
        photo_id = _new_id("p")
        add_photo({"id": photo_id, "url": photo_url, "createdAt": int(time.time() * 1000)})

        try:
            detections = detect_clothing(str(src))
        except Exception as e:
            logger.exception("识别失败：%s", e)
            detections = []

        items_for_photo = []
        for meta in detections:
            out_name = _new_id("it") + ".png"
            out_path = Path(config.PATHS["ITEMS"]) / out_name
            try:
                seg = extract_item(str(src), meta)
                if seg["imageUrl"].startswith(("http://", "https://")):
                    download_to_local(seg["imageUrl"], str(out_path))
                    image_url = f"/items/{out_name}"
                    image_path = str(out_path)
                else:
                    image_url = seg["imageUrl"]
                    image_path = seg["imagePath"]
            except Exception as e:
                logger.exception("分割失败：%s", e)
                continue
            item = {
                "id": _new_id("it"),
                "category": meta["category"],
                "color": meta["color"],
                "season": meta["season"],
                "material": meta["material"],
                "style": meta["style"],
                "fit": meta["fit"],
                "pattern": meta["pattern"],
                "brand": meta["brand"],
                "hasLogo": meta["hasLogo"],
                "imageUrl": image_url,
                "imagePath": image_path,
                "transparent": seg["transparent"],
                "segmentMethod": seg["segmentMethod"],
                "sourcePhoto": photo_url,
                "createdAt": int(time.time() * 1000),
            }
            new_items.append(item)
            items_for_photo.append(item)

        result.append({"photoId": photo_id, "photoUrl": photo_url, "items": items_for_photo})

    if new_items:
        add_items(new_items)

    return {"ok": True, "demoMode": config.DEMO_MODE, "result": result}


@app.post("/api/analyze")
def api_analyze(photos: list[UploadFile] = File(..., description="照片文件，字段名 photos")):
    """第一步：仅用 VL 视觉模型分析出候选单品，不分割、不入库。"""
    if not photos:
        raise HTTPException(status_code=400, detail="未收到照片")
    upload = photos[0]
    src = _save_upload(upload)
    photo_url = f"/uploads/{src.name}"
    photo_id = _new_id("p")
    add_photo({"id": photo_id, "url": photo_url, "createdAt": int(time.time() * 1000)})

    try:
        candidates = detect_clothing(str(src))
    except Exception as e:
        logger.exception("VL 分析失败：%s", e)
        candidates = []

    return {"photoId": photo_id, "photoUrl": photo_url, "candidates": candidates}


@app.post("/api/segment")
def api_segment(payload: dict = Body(...)):
    """第二步：对确认的单品做分割，生成预览图（不入库）。"""
    photo_url = payload.get("photoUrl")
    items_in = payload.get("items") or []
    if not photo_url or not items_in:
        raise HTTPException(status_code=400, detail="缺少 photoUrl 或 items")

    src = Path(config.PATHS["UPLOADS"]) / Path(photo_url).name
    if not src.exists():
        raise HTTPException(status_code=404, detail="源图不存在")

    out = []
    for meta in items_in:
        try:
            seg = extract_item(str(src), meta)
        except Exception as e:
            logger.exception("分割失败：%s", e)
            continue
        out.append(
            {
                **meta,
                "id": _new_id("it"),
                "imageUrl": seg["imageUrl"],      # Qwen OSS 临时地址，供前端预览
                "imagePath": "",                   # 入库下载后再填充本地路径
                "transparent": seg["transparent"],
                "segmentMethod": seg["segmentMethod"],
                "sourcePhoto": photo_url,
            }
        )
    return {"items": out}


@app.post("/api/commit")
def api_commit(payload: dict = Body(...)):
    """第三步：将确认的单品正式入库（同时把 OSS 预览图下载保存为本地图片）。"""
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="没有可入库的单品")

    now = int(time.time() * 1000)
    for it in items:
        it["createdAt"] = now
        # 若 imageUrl 为远程 OSS 地址且尚未落地，则下载到本地 items/
        url = it.get("imageUrl", "")
        if url.startswith("http://") or url.startswith("https://"):
            try:
                out_name = _new_id("it") + ".png"
                out_path = Path(config.PATHS["ITEMS"]) / out_name
                download_to_local(url, str(out_path))
                it["imageUrl"] = f"/items/{out_name}"
                it["imagePath"] = str(out_path)
            except Exception as e:
                logger.exception("OSS 图片下载失败：%s", e)
    add_items(items)
    return {"ok": True, "count": len(items)}


@app.get("/api/items")
def api_items():
    return get_items()


@app.get("/api/items/{item_id}")
def api_item(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="单品不存在")
    return item


@app.delete("/api/items/{item_id}")
def api_delete(item_id: str):
    ok = delete_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="单品不存在")
    return {"ok": True}


@app.get("/api/stats")
def api_stats():
    return get_stats()


# ---------------- 静态资源 ----------------
app.mount("/uploads", StaticFiles(directory=config.PATHS["UPLOADS"]), name="uploads")
app.mount("/items", StaticFiles(directory=config.PATHS["ITEMS"]), name="items")

# 生产构建后托管前端（存在 frontend/dist 时）
_dist = Path(config.BACKEND_DIR).parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)
