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

from fastapi import Body, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# 确保无论从哪个工作目录启动都能导入同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import jwt_token
from qwen import detect_clothing
from segment import download_to_local, extract_item
from security import ContentRiskError, check_image, check_text
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
    get_user,
    upsert_user,
    save_outfit,
    save_tryon_record,
    save_user_photo,
)
from tryon import virtual_tryon

# ---------- 日志：同时输出到控制台和 backend/logs/app.log ----------
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_DIR / "app.log"), encoding="utf-8"),
    ],
)
# 抑制第三方库的 DEBUG 日志
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger("app")

config.ensure_dirs()
from store import init_db
try:
    init_db()
except Exception as e:
    logger.exception("MySQL 数据库初始化失败：%s", e)

app = FastAPI(title="AI 数字衣橱", version="1.0.0")

# 内容安全违规：统一返回 400 + 简洁提示（不暴露具体命中细节）
@app.exception_handler(ContentRiskError)
def _content_risk_handler(request, exc: ContentRiskError):
    logger.warning("内容安全拦截：%s", exc.message)
    return JSONResponse(status_code=400, content={"detail": exc.message, "risk": True})

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
    dest = Path(config.UPLOADS) / name
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    dest.write_bytes(data)
    return dest


def get_openid(request: Request) -> str:
    """从 Authorization: Bearer <jwt> 头解析 openid（校验签名与有效期）。"""
    auth = request.headers.get("Authorization", "") or ""
    if auth.startswith("Bearer "):
        return jwt_token.decode_token(auth[7:].strip())
    return ""


def require_openid(request: Request) -> str:
    """必须登录：无有效令牌（JWT 校验失败/过期）直接 401。"""
    openid = get_openid(request)
    if not openid:
        raise HTTPException(status_code=401, detail="请先登录")
    return openid


# 所有衣橱数据接口都需要登录态，使用 FastAPI dependency 注入 openid


@app.get("/api/config")
def api_config():
    return {
        "demoMode": config.DEMO_MODE,
        "visionModel": config.QWEN_MODEL,
        "imageModel": config.IMAGE_MODEL,
        "cutoutEnabled": config.ENABLE_CUTOUT,
    }


@app.post("/api/process")
def api_process(
    photos: list[UploadFile] = File(..., description="照片文件，字段名 photos"),
    openid: str = Depends(require_openid),
):
    if not photos:
        raise HTTPException(status_code=400, detail="未收到照片")
    photos = photos[:UPLOAD_MAX]

    result = []
    new_items = []
    for upload in photos:
        src = _save_upload(upload)
        photo_url = f"/uploads/{src.name}"
        photo_id = _new_id("p")
        add_photo({"id": photo_id, "url": photo_url, "createdAt": int(time.time() * 1000)}, openid=openid)

        try:
            detections = detect_clothing(str(src))
        except Exception as e:
            logger.exception("识别失败：%s", e)
            detections = []

        items_for_photo = []
        for meta in detections:
            out_name = _new_id("it") + ".png"
            out_path = Path(config.ITEMS) / out_name
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
        add_items(new_items, openid=openid)

    return {"ok": True, "demoMode": config.DEMO_MODE, "result": result}


@app.post("/api/analyze")
def api_analyze(
    photos: list[UploadFile] = File(..., description="照片文件，字段名 photos"),
    openid: str = Depends(require_openid),
):
    """第一步：仅用 VL 视觉模型分析出候选单品，不分割、不入库。"""
    if not photos:
        raise HTTPException(status_code=400, detail="未收到照片")
    upload = photos[0]
    src = _save_upload(upload)
    photo_url = f"/uploads/{src.name}"
    photo_id = _new_id("p")
    add_photo({"id": photo_id, "url": photo_url, "createdAt": int(time.time() * 1000)}, openid=openid)

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

    src = Path(config.UPLOADS) / Path(photo_url).name
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
def api_commit(payload: dict = Body(...), openid: str = Depends(require_openid)):
    """第三步：将确认的单品正式入库（同时把 OSS 预览图下载保存为本地图片）。"""
    items = payload.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="没有可入库的单品")

    now = int(time.time() * 1000)
    for it in items:
        if not it.get("id"):
            it["id"] = _new_id("it")
        it["createdAt"] = now
        # 对外发布场景：入库单品的图片须过内容安全
        img_url = it.get("imageUrl", "")
        if img_url.startswith("http://") or img_url.startswith("https://"):
            # 远程图先下载再检测
            try:
                out_name = _new_id("it") + ".png"
                out_path = Path(config.ITEMS) / out_name
                download_to_local(img_url, str(out_path))
                it["imageUrl"] = f"/items/{out_name}"
                it["imagePath"] = str(out_path)
                check_image(str(out_path))
            except Exception as e:
                logger.exception("OSS 图片下载/检测失败：%s", e)
        elif img_url.startswith("/items/"):
            check_image(str(Path(config.ROOT) / img_url.lstrip("/")))
        # 若 imageUrl 为远程 OSS 地址且尚未落地，则下载到本地 items/
        url = it.get("imageUrl", "")
        if url.startswith("http://") or url.startswith("https://"):
            try:
                out_name = _new_id("it") + ".png"
                out_path = Path(config.ITEMS) / out_name
                download_to_local(url, str(out_path))
                it["imageUrl"] = f"/items/{out_name}"
                it["imagePath"] = str(out_path)
            except Exception as e:
                logger.exception("OSS 图片下载失败：%s", e)
    add_items(items, openid=openid)
    return {"ok": True, "count": len(items)}


@app.get("/api/items")
def api_items(openid: str = Depends(require_openid)):
    return get_items(openid)


@app.get("/api/items/{item_id}")
def api_item(item_id: str, openid: str = Depends(require_openid)):
    item = get_item(item_id, openid)
    if not item:
        raise HTTPException(status_code=404, detail="单品不存在")
    return item


@app.delete("/api/items/{item_id}")
def api_delete(item_id: str, openid: str = Depends(require_openid)):
    ok = delete_item(item_id, openid)
    if not ok:
        raise HTTPException(status_code=404, detail="单品不存在")
    return {"ok": True}


@app.get("/api/stats")
def api_stats(openid: str = Depends(require_openid)):
    return get_stats(openid)


# ---------------- 用户照片（AI 试穿底图） ----------------

@app.get("/api/user/photo")
def api_get_user_photo(openid: str = Depends(require_openid)):
    """获取当前用户的全身照信息。"""
    p = get_user_photo(openid)
    if not p:
        raise HTTPException(status_code=404, detail="尚未上传全身照")
    return p


@app.post("/api/user/photo")
def api_upload_user_photo(
    photo: UploadFile = File(..., description="全身正面照"),
    openid: str = Depends(require_openid),
):
    """上传/更新用户的全身正面照。"""
    src = _save_upload(photo)
    # 对外发布场景：上传的全身照须过内容安全
    check_image(str(src))
    url = f"/uploads/{src.name}"
    info = {
        "openid": openid,
        "url": url,
        "path": str(src),
        "createdAt": int(time.time() * 1000),
    }
    save_user_photo(info)
    return {"ok": True, "photo": info}


@app.post("/api/user/avatar")
def api_upload_avatar(
    avatar: UploadFile = File(..., description="用户头像"),
    openid: str = Depends(require_openid),
):
    """上传用户头像，返回可访问 URL（供小程序 chooseAvatar 结果持久化）。"""
    src = _save_upload(avatar)
    check_image(str(src))
    url = f"/uploads/{src.name}"
    return {"ok": True, "url": url}


# ---------------- AI 试穿 ----------------

@app.post("/api/tryon")
def api_tryon(payload: dict = Body(...), openid: str = Depends(require_openid)):
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

    # 取用户全身照（按当前用户隔离）
    user_photo = get_user_photo(openid)
    if not user_photo:
        raise HTTPException(status_code=400, detail="请先在「我的」页面上传您的全身正面照")

    photo_path = user_photo.get("path")
    if not photo_path or not Path(photo_path).exists():
        raise HTTPException(status_code=404, detail="全身照文件丢失，请重新上传")

    # 对外发布场景：试穿底图（用户照）+ 选中的单品图都需过内容安全
    check_image(photo_path)
    for it in selected:
        img_path = it.get("imagePath") or ""
        if not img_path and (it.get("imageUrl") or "").startswith("/"):
            img_path = str(Path(config.ROOT) / it["imageUrl"].lstrip("/"))
        if img_path:
            check_image(img_path)

    # 按 itemId 取真实单品（仅当前用户）
    all_items = get_items(openid)
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
            img_path = str(Path(config.ROOT) / it["imageUrl"].lstrip("/"))
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
            img_path = Path(config.TRYON_RESULTS) / img_name
            download_to_local(result_url, str(img_path))
            result_url = f"/tryon_results/{img_name}"
        except Exception as e:
            logger.exception("试穿结果图落地失败：%s", e)
            raise HTTPException(status_code=500, detail=f"试穿结果图保存失败：{e}")

    return {"ok": True, "resultUrl": result_url}


# ---------------- 试穿记录（保存/查询/删除） ----------------

@app.post("/api/tryon/save")
def api_save_tryon(payload: dict = Body(...), openid: str = Depends(require_openid)):
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

    # 从衣橱取单品快照（仅当前用户）
    all_items = get_items(openid)
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
    img_path = Path(config.TRYON_RESULTS) / img_name
    if result_url.startswith("http://") or result_url.startswith("https://"):
        logger.info("开始下载试穿结果图: %s", result_url[:120])
        try:
            download_to_local(result_url, str(img_path))
        except Exception as e:
            logger.exception("试穿结果图下载失败: url=%s error=%s", result_url[:200], e)
            raise HTTPException(status_code=500, detail=f"保存结果图失败: {e}")
    elif result_url.startswith("/tryon_results/"):
        # 已是本地文件，直接复制（无需重新下载）
        src = Path(config.ROOT) / result_url.lstrip("/")
        if src.exists():
            import shutil
            shutil.copy2(str(src), str(img_path))
        else:
            raise HTTPException(status_code=400, detail="结果图文件不存在")
    else:
        raise HTTPException(status_code=400, detail="结果图 URL 无效，请联系开发者")

    record = {
        "id": _new_id("tr"),
        "openid": openid,
        "itemIds": item_ids,
        "items": item_snapshots,
        "resultUrl": f"/tryon_results/{img_name}",
        "imagePath": str(img_path),
        "createdAt": int(time.time() * 1000),
    }
    save_tryon_record(record)
    return {"ok": True, "record": record}


@app.get("/api/tryon/records")
def api_tryon_records(openid: str = Depends(require_openid)):
    """获取当前用户已保存的试穿记录。"""
    return get_tryon_records(openid)


# ---------------- 内容安全检测（供小程序发布场景调用） ----------------

@app.post("/api/security/check")
def api_security_check(payload: dict = Body(...)):
    """
    小程序发布前的内容安全预检：
      - text: 可选，待检测文本（备注等）
      - imageUrls: 可选，待检测图片的本地路径列表（/uploads/...、/items/...、/tryon_results/...）
    命中违规统一返回 400 + {"detail": "所发布内容含违规信息", "risk": true}
    """
    text = payload.get("text", "") or ""
    image_urls = payload.get("imageUrls", []) or []

    if text:
        check_text(text, scene=2)

    checked_any = False
    for u in image_urls:
        if not u:
            continue
        path = u if (u.startswith("/") is False and not u.startswith("http")) else str(Path(config.ROOT) / u.lstrip("/"))
        if u.startswith("http://") or u.startswith("https://"):
            # 远程图：先落地再检测
            try:
                name = _new_id("sec") + ".png"
                p = Path(config.UPLOADS) / name
                download_to_local(u, str(p))
                check_image(str(p))
                checked_any = True
            except Exception as e:
                logger.warning("远程图内容安全预检失败，跳过: %s", e)
            continue
        check_image(path)
        checked_any = True

    return {"ok": True, "checked": bool(text) or checked_any}


@app.delete("/api/tryon/records/{record_id}")
def api_delete_tryon(record_id: str, openid: str = Depends(require_openid)):
    """删除指定的试穿记录。"""
    ok = delete_tryon_record(record_id, openid)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


# ---------------- 日历穿搭（outfits） ----------------

@app.get("/api/outfits")
def api_outfits(openid: str = Depends(require_openid), date: str = None):
    """获取日历穿搭：传 date 取某天，否则返回全部（仅当前用户）。"""
    if date:
        o = get_outfit(date, openid)
        if not o:
            raise HTTPException(status_code=404, detail="当天没有穿搭记录")
        return o
    return get_outfits(openid)


@app.post("/api/outfits")
def api_save_outfit(payload: dict = Body(...), openid: str = Depends(require_openid)):
    """新增或更新某天的穿搭（按 date upsert）。

    前端只传 {category, itemId, imageUrl?, name?}，后端根据 itemId 从真实衣橱
    解析出持久化的本地图片地址与真实属性，确保落库数据是真实可长期访问的。
    """
    date = payload.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="缺少 date")

    # 对外发布场景：日历备注属用户公开文本，须过内容安全
    note = payload.get("note", "") or ""
    check_text(note, scene=2)

    raw_items = payload.get("items", []) or []
    real_items = get_items(openid)  # 真实衣橱单品（仅当前用户、已归一化、含本地 imageUrl）
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
        "openid": openid,
        "items": clean_items,
        "note": payload.get("note", ""),
        "updatedAt": int(time.time() * 1000),
    }
    save_outfit(outfit)
    return {"ok": True, "outfit": outfit}


@app.delete("/api/outfits/{date}")
def api_delete_outfit(date: str, openid: str = Depends(require_openid)):
    ok = delete_outfit(date, openid)
    if not ok:
        raise HTTPException(status_code=404, detail="当天没有穿搭记录")
    return {"ok": True}


# ---------------- 微信授权登录 ----------------

def _wx_code2session(code: str) -> dict:
    """调用微信 auth.code2Session 换取 openid / session_key。"""
    if not (config.WX_APPID and config.WX_SECRET):
        raise HTTPException(status_code=500, detail="服务端未配置微信 AppID/Secret")
    import requests

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": config.WX_APPID,
        "secret": config.WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
    except Exception as e:
        logger.exception("微信 code2Session 请求失败：%s", e)
        raise HTTPException(status_code=502, detail="微信登录服务异常")
    if "openid" not in data:
        errcode = data.get("errcode")
        errmsg = data.get("errmsg", "未知错误")
        logger.warning("微信 code2Session 返回错误：%s %s", errcode, errmsg)
        raise HTTPException(status_code=401, detail=f"微信登录失败({errcode})")
    return data


@app.post("/api/auth/login")
def api_auth_login(body: dict = Body(default={})):
    """小程序 wx.login 拿到的 code 换取 openid，并把用户写入库。"""
    code = body.get("code") or ""
    if not code:
        raise HTTPException(status_code=400, detail="缺少 code")
    wx_data = _wx_code2session(code)
    openid = wx_data["openid"]
    user = upsert_user(openid)  # 首次登录仅建记录
    token = jwt_token.create_token(openid)
    return {
        "ok": True,
        "openid": openid,
        "token": token,
        "user": user,
    }


@app.post("/api/user/profile")
def api_update_profile(body: dict = Body(default={}), openid: str = Depends(require_openid)):
    """更新昵称 / 头像（openid 从 JWT 登录态解析，不再由前端明文传入）。"""
    nickname = (body.get("nickname") or "").strip()
    avatar = (body.get("avatar") or "").strip()
    user = upsert_user(openid, nickname=nickname, avatar=avatar)
    return {"ok": True, "user": user}


@app.get("/api/user/profile")
def api_get_profile(openid: str = Depends(require_openid)):
    """获取用户信息（根据登录态返回 created_at 等）。"""
    user = get_user(openid)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True, "user": user}


# ---------------- 静态资源 ----------------
app.mount("/uploads", StaticFiles(directory=config.UPLOADS), name="uploads")
app.mount("/items", StaticFiles(directory=config.ITEMS), name="items")
app.mount("/tryon_results", StaticFiles(directory=config.TRYON_RESULTS), name="tryon_results")

# 生产构建后托管前端（存在 frontend/dist 时）
_dist = config.ROOT.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)
