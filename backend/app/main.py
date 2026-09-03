"""辽轨智能实训能力评估平台 API。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.controllers.admin import router as admin_router
from app.adapters.controllers.dashboard import router as dashboard_detail_router
from app.adapters.controllers.student import router as student_detail_router
from app.config import settings
from app.database import init_db
from app.routers import (
    abilities_router,
    auth_router,
    dashboard_router,
    environment_router,
    reports_router,
    scores_router,
    students_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    from app.init_data import init_mock_data

    await init_mock_data()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="辽宁铁道职业技术学院智能实训能力评估平台 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(scores_router)
app.include_router(abilities_router)
app.include_router(environment_router)
app.include_router(reports_router)
app.include_router(dashboard_router)
app.include_router(admin_router, prefix="/api/v1/admin", tags=["系统管理"])
app.include_router(
    dashboard_detail_router,
    prefix="/api/v1/dashboard",
    tags=["大屏明细"],
)
app.include_router(
    student_detail_router,
    prefix="/api/v1/students",
    tags=["学生个人中心"],
)
app.include_router(students_router)


@app.get("/")
async def root():
    return {
        "message": "辽轨智能实训能力评估平台 API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "database": "connected"}
