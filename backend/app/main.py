"""
辽轨智能实训能力评估平台 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.adapters.controllers import (
    auth_router,
    student_router,
    teacher_router,
    dashboard_router,
    admin_router,
    training_router,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")
    
    # 加载 Mock 数据
    from app.services.data_loader import load_mock_data
    await load_mock_data()
    logger.info("Mock 数据加载完成")
    
    yield
    
    logger.info("应用关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="辽宁铁路职业技术学院智能实训能力评估平台 API",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["https://shixun.demo.densematrix.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(student_router, prefix="/api/v1/students", tags=["学生端"])
app.include_router(teacher_router, prefix="/api/v1/teachers", tags=["教师端"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["大屏展示"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["管理后台"])
app.include_router(training_router, prefix="/api/v1/training", tags=["实训与AI"])


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用辽轨智能实训能力评估平台 API",
        "docs": "/docs",
        "health": "/health"
    }
