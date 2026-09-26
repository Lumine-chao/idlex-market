"""闲置易二手交易平台 服务端入口"""
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import errors
# 真实路由
import app.routers.auth as auth_router
import app.routers.users as users_router
import app.routers.categories as cat_router
import app.routers.uploads as up_router
import app.routers.items as item_router
import app.routers.search as search_router
import app.routers.im as im_router
import app.routers.orders as order_router
import app.routers.reviews as review_router
import app.routers.reports as report_router
import app.routers.admin as admin_router
from .seed import seed_demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_demo()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(errors.BizError)
async def biz_error_handler(request: Request, exc: errors.BizError):
    return JSONResponse(status_code=exc.http_status, content={
        "code": exc.code, "message": exc.message, "data": exc.data})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    if isinstance(exc, errors.BizError):
        return JSONResponse(status_code=exc.http_status, content={
            "code": exc.code, "message": exc.message, "data": exc.data})
    return JSONResponse(status_code=500, content={
        "code": errors.ErrorCodes.SYSTEM_BUSY, "message": errors.MSG["system.busy"],
        "data": None})


# 业务路由
for r in (auth_router, users_router, cat_router, up_router, item_router,
          search_router, im_router, order_router, review_router, report_router,
          admin_router):
    app.include_router(r.router)


@app.get("/api/health")
async def health():
    return {"code": 0, "message": "ok", "data": {"service": settings.app_name}}


# 静态资源（上传图片）与前端产物
_uploads_dir = Path(settings.upload_dir)
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_uploads_dir)), name="static")

_web_dist = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if _web_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_web_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        # 未匹配到的接口路径直接返回 404 JSON，避免被兜底成 HTML 而让前端静默失败
        if full_path.startswith(("api/", "static/")):
            return JSONResponse(status_code=404, content={
                "code": errors.ErrorCodes.NOT_FOUND, "message": "接口不存在", "data": None})
        target = _web_dist / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        idx = _web_dist / "index.html"
        if idx.exists():
            # 入口 HTML 不缓存，避免前端重新构建后浏览器仍加载旧哈希资源
            return FileResponse(idx, headers={"Cache-Control": "no-cache, must-revalidate"})
        return JSONResponse({"code": 404, "message": "not found"})