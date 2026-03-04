from app.routers.auth import router as auth_router
from app.routers.scores import router as scores_router
from app.routers.abilities import router as abilities_router
from app.routers.environment import router as environment_router
from app.routers.reports import router as reports_router
from app.routers.dashboard import router as dashboard_router
from app.routers.students import router as students_router

__all__ = [
    "auth_router",
    "scores_router",
    "abilities_router",
    "environment_router",
    "reports_router",
    "dashboard_router",
    "students_router",
]
