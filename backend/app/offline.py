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
    settings.RELEASE_MODE = MODE != "demo"
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
        from app.services.operations_runtime import worker
        await worker.start()
    try:
        yield
    finally:
        if MODE == "demo":
            await sync_scheduler.stop()
        else:
            await worker.stop()


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
            (method not in {"GET", "HEAD", "OPTIONS"} and (
                path == "/api/v1/admin/sync" or path.startswith("/api/v1/admin/sync/")
                or path.startswith("/api/v1/operations/sync")
                or path.startswith("/api/v1/admin/operations/sync")
            ))
            or (method == "DELETE" and path.startswith("/api/v1/admin/"))
        )
        if MODE == "pilot" and path.startswith("/api/") and not path.startswith(("/api/v1/auth/login", "/api/v1/sso/")):
            if scope["type"] == "websocket":
                await send({"type":"websocket.close","code":1008})
                return
            try:
                from app.services.account_security import validate_account
                token = dict(scope.get("headers",[])).get(b"authorization",b"").decode()
                if not token.startswith("Bearer "):
                    raise HTTPException(401,"请先登录")
                data = AuthService.decode_token(token[7:], token_type="refresh" if path=="/api/v1/auth/refresh" else "access")
                async with AsyncSessionLocal() as db:
                    service=AuthService(db)
                    try:
                        current=await service.get_current_user(data.user_id,data.version)
                    except HTTPException as exc:
                        if exc.status_code==404:
                            raise HTTPException(401,"账号不存在") from exc
                        raise
                    # Request-local reuse only: every new request checks revocation
                    # against the database, without duplicating that query in routers.
                    scope.setdefault("state",{})["verified_user_response"]=current
                    scope["state"]["verified_user_model"]=service.verified_user
                    if path.startswith("/api/v1/dashboard") and current.role != "admin":
                        raise HTTPException(403,"校内大屏仅限管理员，学生和教师请使用各自统计页面")
            except HTTPException as exc:
                await JSONResponse(status_code=exc.status_code,content={"detail":exc.detail})(scope,receive,send)
                return
        if blocked and scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if blocked and scope["type"] == "http":
            response = JSONResponse(status_code=409, content={"detail": "校内部署禁止演示同步和删除历史对象；请使用上线管理中的真实导入或停用功能。"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


# Register API routes without invoking the demo application's lifespan.
for route in api.routes:
    if getattr(route,"path",None) not in {"/", "/health", "/docs", "/redoc", "/docs/oauth2-redirect"}:
        site.router.routes.append(route)


@site.get("/{path:path}")
async def static_site(path: str):
    if path.startswith(("api/", "docs", "redoc")):
        raise HTTPException(404)
    candidate = (STATIC / path).resolve()
    if not candidate.is_relative_to(STATIC):
        raise HTTPException(404)
    if candidate.is_file() and path != "index.html":
        return FileResponse(candidate)
    if Path(path).suffix and path != "index.html":
        raise HTTPException(404)
    index = (STATIC / "index.html").read_text()
    runtime = "<script>window.__SHIXUN_DEMO__=" + json.dumps(MODE == "demo") + ";</script>"
    return HTMLResponse(index.replace("<head>", "<head>" + runtime), headers={"Cache-Control": "no-store"})


from app.services.operations_runtime import OperationalMiddleware
app = OperationalMiddleware(PilotBoundary(site))
