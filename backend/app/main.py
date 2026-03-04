from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import (
    auth_router,
    scores_router,
    abilities_router,
    environment_router,
    reports_router,
    dashboard_router,
    students_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    # Load mock data if database is empty
    from app.init_data import init_mock_data
    await init_mock_data()
    
    yield
    
    # Shutdown
    pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="辽宁铁道职业技术学院智能实训能力评估平台 API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(scores_router)
app.include_router(abilities_router)
app.include_router(environment_router)
app.include_router(reports_router)
app.include_router(dashboard_router)
app.include_router(students_router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
