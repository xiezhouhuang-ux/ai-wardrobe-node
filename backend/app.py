"""
AI 衣橱后端入口。

职责：创建 FastAPI 实例、配置中间件 / CORS / 异常处理 / 静态资源 / 启动入口，
并将各业务域路由（routes/）挂载进来。具体业务逻辑下沉到 services/ 与 store.py，
鉴权依赖与文件工具在 core/ 共享复用。
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import store
from routes import routers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title="AI 衣橱后端", version="1.0")

# 跨域：本地开发（微信小程序 / 后台前端）任意来源可访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def fix_content_type(request: Request, call_next):
    """某些网关把 JSON 误标成 text/plain，这里纠正为 application/json。"""
    resp = await call_next(request)
    if resp.headers.get("content-type", "").startswith("text/plain"):
        resp.headers["content-type"] = "application/json; charset=utf-8"
    return resp


@app.exception_handler(Exception)
async def global_exc(request: Request, exc: Exception):
    logger.exception("未捕获异常: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


@app.get("/api/health")
def api_health():
    return {"ok": True, "service": "ai-wardrobe", "demo": config.DEMO_MODE}


# 挂载业务路由
for _r in routers:
    app.include_router(_r)


# 静态资源：统一放在 uploads/ 下，再用子文件夹区分（photos / items / tryon_results）
# 只需挂载一次 uploads，子目录（如 /uploads/items/xxx.png）自动可访问。
def _mount_static(folder: str):
    path = Path(config.ROOT) / folder
    path.mkdir(parents=True, exist_ok=True)
    app.mount(f"/{folder}", StaticFiles(directory=str(path)), name=f"static_{folder}")


_mount_static("uploads")


def run():
    import uvicorn

    config.ensure_dirs()
    store.init_db()
    uvicorn.run("app:app", host="0.0.0.0", port=config.PORT, reload=False)


if __name__ == "__main__":
    run()
