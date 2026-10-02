"""Single-process, offline-installable site; clean pilot mode is not acceptance."""
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy import select, text

from app.main import app as api
from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.operations import SystemSetting
from app.services.auth import AuthService

MODE = os.getenv("DEPLOYMENT_MODE", "pilot")
STATIC = Path(os.getenv("STATIC_DIR", "/app/static")).resolve()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if MODE not in {"pilot", "demo"}:
        raise RuntimeError("DEPLOYMENT_MODE must be pilot or demo")
    if len(settings.SECRET_KEY) < 32 or settings.SECRET_KEY.startswith("liaoning-railway-training-demo"):
        raise RuntimeError("Set a unique SECRET_KEY with at least 32 characters")
    await init_db()
    async with AsyncSessionLocal() as db:
        marker = await db.get(SystemSetting, "offline_deployment_mode")
        populated = (await db.execute(select(User.id).limit(1))).scalar_one_or_none()
        if marker and marker.value.get("mode") != MODE:
            raise RuntimeError("Do not switch demo/pilot on an existing volume; use a new volume")
        if not marker:
            if populated:
                raise RuntimeError("Unmarked existing database: migration review required")
            db.add(SystemSetting(key="offline_deployment_mode", value={"mode": MODE}))
            await db.commit()
    if MODE == "demo":
        from app.init_data import init_mock_data
        await init_mock_data()
        from app.services.scheduler import sync_scheduler
        sync_scheduler.start()
    else:
        async with AsyncSessionLocal() as db:
            existing = (await db.execute(select(User.id).limit(1))).scalar_one_or_none()
            if not existing:
                password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
                if len(password) < 16:
                    raise RuntimeError("Set BOOTSTRAP_ADMIN_PASSWORD with at least 16 characters")
                db.add(User(id=str(uuid.uuid4()), username=os.getenv("BOOTSTRAP_ADMIN_USER", "admin"),
                            name="系统管理员", role=UserRole.ADMIN,
                            password_hash=AuthService.get_password_hash(password)))
                await db.commit()
    try:
        yield
    finally:
        if MODE == "demo":
            await sync_scheduler.stop()


site = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@site.get("/health")
async def readiness():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "mode": MODE,
                "release_scope": "pilot-not-production-acceptance"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "unavailable"})


class PilotBoundary:
    """Prevent demo sync and unscoped dashboard routes from accepting real data."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "").rstrip("/")
        method = scope.get("method", "GET")
        blocked = MODE == "pilot" and (
            path.startswith("/api/v1/dashboard")
            or (method not in {"GET", "HEAD", "OPTIONS"} and (
                path == "/api/v1/admin/sync" or path.startswith("/api/v1/admin/sync/")
                or path.startswith("/api/v1/operations/sync")
                or path.startswith("/api/v1/admin/operations/sync")
            ))
        )
        if blocked and scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if blocked and scope["type"] == "http":
            response = JSONResponse(status_code=503, content={"detail": "试部署包未开放演示同步及公共大屏；真实数据接入和权限验收完成后开放。"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


# Register API routes without invoking the demo application's lifespan.
for route in api.routes:
    if route.path not in {"/", "/health", "/docs", "/redoc", "/docs/oauth2-redirect"}:
        site.router.routes.append(route)


@site.get("/{path:path}")
async def static_site(path: str):
    if path.startswith(("api/", "docs", "redoc")):
        raise HTTPException(404)
    candidate = (STATIC / path).resolve()
    if not candidate.is_relative_to(STATIC):
        raise HTTPException(404)
    if candidate.is_file():
        return FileResponse(candidate)
    if Path(path).suffix:
        raise HTTPException(404)
    index = (STATIC / "index.html").read_text()
    runtime = "<script>window.__SHIXUN_DEMO__=" + json.dumps(MODE == "demo") + ";</script>"
    return HTMLResponse(index.replace("<head>", "<head>" + runtime), headers={"Cache-Control": "no-store"})


app = PilotBoundary(site)
