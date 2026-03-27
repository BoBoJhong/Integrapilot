"""FastAPI 應用工廠：靜態資源、例外處理、路由掛載。"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api import db
from api import helpers as h
from api.config import setup_dirs, setup_env, UI_DIST
from api.limiter_ext import limiter
from api.routes_api import router as api_router


def create_app() -> FastAPI:
    setup_env()
    setup_dirs()
    db.run_migrations()
    default_agent = h.default_agents()[0]
    db.upsert_default_agent(h.now_taipei(), default_agent)

    app = FastAPI(title="IntegraPilot")

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        if isinstance(exc, RequestValidationError):
            return JSONResponse(status_code=422, content={"detail": exc.errors()})
        return JSONResponse(
            status_code=500,
            content={"detail": f"伺服器內部錯誤：{exc!s}"},
        )

    _assets_dir = UI_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="vite_assets")

    app.include_router(api_router)

    @app.get("/health")
    def health() -> dict:
        dist_ok = (UI_DIST / "index.html").is_file()
        return {
            "ok": True,
            "service": "integrapilot",
            "ui_dist": dist_ok,
        }

    @app.get("/")
    def root() -> FileResponse:
        dist_index = UI_DIST / "index.html"
        if dist_index.exists():
            return FileResponse(str(dist_index))
        raise HTTPException(
            status_code=503,
            detail="尚未建置前端靜態檔；請在 frontend 目錄執行 npm install && npm run build，產出 ui/dist。",
        )

    return app
