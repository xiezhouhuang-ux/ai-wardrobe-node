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
from store import (
    add_items,
    add_photo,
    delete_item,
    delete_outfit,
    delete_tryon_record,
    get_item,
    get_items,
    get_outfit,
    get_outfits,
    get_stats,
    get_tryon_records,
    get_user_photo,
    save_outfit,
    save_tryon_record,
    save_user_photo,
)
from tryon import virtual_tryon

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
    """第二步：对确认的单品做分割，生成预览图（不入库）。

    每次只上传一件单品：接收 photoUrl + 单个 item 元数据，返回该单品的分割结果。
    """
    photo_url = payload.get("photoUrl")
    meta = payload.get("item")
    if not photo_url or not meta:
        raise HTTPException(status_code=400, detail="缺少 photoUrl 或 item")

    src = Path(config.PATHS["UPLOADS"]) / Path(photo_url).name
    if not src.exists():
        raise HTTPException(status_code=404, detail="源图不存在")

    try:
        seg = extract_item(str(src), meta)
    except Exception as e:
        logger.exception("分割失败：%s", e)
        raise HTTPException(status_code=500, detail=f"单品分割失败：{e}")

    return {
        **meta,
        "id": _new_id("it"),
        "imageUrl": seg["imageUrl"],      # Qwen OSS 临时地址，供前端预览
        "imagePath": "",                   # 入库下载后再填充本地路径
        "transparent": seg["transparent"],
        "segmentMethod": seg["segmentMethod"],
        "sourcePhoto": photo_url,
    }


@app.post("/api/commit")
def api_commit(payload: dict = Body(...)):
    """第三步：将确认的单品正式入库（同时把 OSS 预览图下载保存为本地图片）。"""
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="没有可入库的单品")

    now = int(time.time() * 1000)
    for it in items:
        if not it.get("id"):
            it["id"] = _new_id("it")
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


# ---------------- 用户照片（AI 试穿底图） ----------------

@app.get("/api/user/photo")
def api_get_user_photo():
    """获取当前用户的全身照信息。"""
    p = get_user_photo()
    if not p:
        raise HTTPException(status_code=404, detail="尚未上传全身照")
    return p


@app.post("/api/user/photo")
def api_upload_user_photo(photo: UploadFile = File(..., description="全身正面照")):
    """上传/更新用户的全身正面照。"""
    src = _save_upload(photo)
    url = f"/uploads/{src.name}"
    info = {
        "url": url,
        "path": str(src),
        "createdAt": int(time.time() * 1000),
    }
    save_user_photo(info)
    return {"ok": True, "photo": info}


# ---------------- AI 试穿 ----------------

@app.post("/api/tryon")
def api_tryon(payload: dict = Body(...)):
    """
    AI 虚拟试穿：将衣橱单品「穿」到用户全身照上。

    输入：
        itemIds: [itemId, ...]   – 选中的衣橱单品 ID 列表

    流程：
        1. 从衣橱按 itemId 取真实单品本地图片
        2. 从 store 取用户全身照
        3. 调用 Qwen 多模态图像生成接口
        4. 返回生成结果图片 URL
    """
    item_ids = payload.get("itemIds") or []
    if not item_ids:
        raise HTTPException(status_code=400, detail="至少选择一件单品")

    # 取用户全身照
    user_photo = get_user_photo()
    if not user_photo:
        raise HTTPException(status_code=400, detail="请先在「我的」页面上传您的全身正面照")

    photo_path = user_photo.get("path")
    if not photo_path or not Path(photo_path).exists():
        raise HTTPException(status_code=404, detail="全身照文件丢失，请重新上传")

    # 按 itemId 取真实单品
    all_items = get_items()
    item_map = {it["id"]: it for it in all_items}
    selected = []
    missing = []
    for iid in item_ids:
        it = item_map.get(iid)
        if it:
            selected.append(it)
        else:
            missing.append(iid)
    if missing:
        raise HTTPException(status_code=404, detail=f"单品不存在: {', '.join(missing)}")
    if not selected:
        raise HTTPException(status_code=400, detail="没有有效的单品")

    # 读取用户全身照字节
    person_bytes = Path(photo_path).read_bytes()

    # 为试穿准备单品信息（需带本地图片路径）
    item_images = []
    for it in selected:
        img_path = it.get("imagePath") or ""
        if not img_path and (it.get("imageUrl") or "").startswith("/"):
            img_path = str(Path(config.PATHS["ROOT"]) / it["imageUrl"].lstrip("/"))
        if not img_path or not Path(img_path).exists():
            logger.warning("单品 %s 图片缺失，跳过: %s", it["id"], img_path)
            continue
        item_images.append({
            "imageUrl": img_path,
            "category": it.get("category", ""),
            "color": it.get("color", ""),
            "style": it.get("style", ""),
        })

    if not item_images:
        raise HTTPException(status_code=400, detail="没有可用的单品图片")

    try:
        result_url = virtual_tryon(person_bytes, item_images)
    except Exception as e:
        logger.exception("虚拟试穿失败")
        raise HTTPException(status_code=500, detail=str(e))

    # 下载 OSS 临时结果图到本地，返回后端本地路径供小程序加载
    if result_url.startswith("http://") or result_url.startswith("https://"):
        try:
            img_name = _new_id("tr") + ".png"
            img_path = Path(config.PATHS["TRYON_RESULTS"]) / img_name
            download_to_local(result_url, str(img_path))
            result_url = f"/tryon_results/{img_name}"
        except Exception as e:
            logger.exception("试穿结果图落地失败：%s", e)
            raise HTTPException(status_code=500, detail=f"试穿结果图保存失败：{e}")

    return {"ok": True, "resultUrl": result_url}


# ---------------- 试穿记录（保存/查询/删除） ----------------

@app.post("/api/tryon/save")
def api_save_tryon(payload: dict = Body(...)):
    """
    保存当前试穿搭配记录：
      - 将试穿结果图从 OSS 下载到本地 tryon_results/
      - 保存搭配单品快照（从衣橱取真实数据）
      - 记录生成时间
    """
    item_ids = payload.get("itemIds") or []
    result_url = payload.get("resultUrl") or ""
    if not item_ids:
        raise HTTPException(status_code=400, detail="请至少选择一件单品")
    if not result_url:
        raise HTTPException(status_code=400, detail="缺少试穿结果图")

    # 从衣橱取单品快照
    all_items = get_items()
    item_map = {it["id"]: it for it in all_items}
    item_snapshots = []
    for iid in item_ids:
        it = item_map.get(iid)
        if it:
            item_snapshots.append({
                "id": it["id"],
                "category": it.get("category", ""),
                "color": it.get("color", ""),
                "style": it.get("style", ""),
                "imageUrl": it.get("imageUrl", ""),
                "name": f'{it.get("color", "")}·{it.get("category", "")}'.strip("·"),
            })

    # 下载结果图到本地
    img_name = _new_id("tr") + ".png"
    img_path = Path(config.PATHS["TRYON_RESULTS"]) / img_name
    if result_url.startswith("http://") or result_url.startswith("https://"):
        logger.info("开始下载试穿结果图: %s", result_url[:120])
        try:
            download_to_local(result_url, str(img_path))
        except Exception as e:
            logger.exception("试穿结果图下载失败: url=%s error=%s", result_url[:200], e)
            raise HTTPException(status_code=500, detail=f"保存结果图失败: {e}")
    elif result_url.startswith("/tryon_results/"):
        # 已是本地文件，直接复制（无需重新下载）
        src = Path(config.PATHS["ROOT"]) / result_url.lstrip("/")
        if src.exists():
            import shutil
            shutil.copy2(str(src), str(img_path))
        else:
            raise HTTPException(status_code=400, detail="结果图文件不存在")
    else:
        raise HTTPException(status_code=400, detail="结果图 URL 无效，请联系开发者")

    record = {
        "id": _new_id("tr"),
        "itemIds": item_ids,
        "items": item_snapshots,
        "resultUrl": f"/tryon_results/{img_name}",
        "imagePath": str(img_path),
        "createdAt": int(time.time() * 1000),
    }
    save_tryon_record(record)
    return {"ok": True, "record": record}


@app.get("/api/tryon/records")
def api_tryon_records():
    """获取所有已保存的试穿记录。"""
    return get_tryon_records()


@app.delete("/api/tryon/records/{record_id}")
def api_delete_tryon(record_id: str):
    """删除指定的试穿记录。"""
    ok = delete_tryon_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


# ---------------- 日历穿搭（outfits） ----------------

@app.get("/api/outfits")
def api_outfits(date: str = None):
    """获取日历穿搭：传 date 取某天，否则返回全部。"""
    if date:
        o = get_outfit(date)
        if not o:
            raise HTTPException(status_code=404, detail="当天没有穿搭记录")
        return o
    return get_outfits()


@app.post("/api/outfits")
def api_save_outfit(payload: dict = Body(...)):
    """新增或更新某天的穿搭（按 date upsert）。

    前端只传 {category, itemId, imageUrl?, name?}，后端根据 itemId 从真实衣橱
    解析出持久化的本地图片地址与真实属性，确保落库数据是真实可长期访问的。
    """
    date = payload.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="缺少 date")

    raw_items = payload.get("items", []) or []
    real_items = get_items()  # 真实衣橱单品（已归一化、含本地 imageUrl）
    real_by_id = {it["id"]: it for it in real_items}

    clean_items = []
    for it in raw_items:
        item_id = it.get("itemId")
        real = real_by_id.get(item_id) if item_id else None
        if not real:
            # 缺少有效 itemId 的条目直接忽略，避免写入脏数据
            continue
        clean_items.append({
            "itemId": item_id,
            "category": real.get("category", it.get("category", "")),
            "imageUrl": real.get("imageUrl") or it.get("imageUrl", ""),
            "name": it.get("name") or real.get("color", "") or real.get("category", ""),
        })

    outfit = {
        "date": date,
        "items": clean_items,
        "note": payload.get("note", ""),
        "updatedAt": int(time.time() * 1000),
    }
    save_outfit(outfit)
    return {"ok": True, "outfit": outfit}


@app.delete("/api/outfits/{date}")
def api_delete_outfit(date: str):
    ok = delete_outfit(date)
    if not ok:
        raise HTTPException(status_code=404, detail="当天没有穿搭记录")
    return {"ok": True}


# ---------------- 静态资源 ----------------
app.mount("/uploads", StaticFiles(directory=config.PATHS["UPLOADS"]), name="uploads")
app.mount("/items", StaticFiles(directory=config.PATHS["ITEMS"]), name="items")
app.mount("/tryon_results", StaticFiles(directory=config.PATHS["TRYON_RESULTS"]), name="tryon_results")

# 生产构建后托管前端（存在 frontend/dist 时）
_dist = config.ROOT.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)
