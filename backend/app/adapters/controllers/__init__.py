from app.adapters.controllers.auth import router as auth_router
from app.adapters.controllers.student import router as student_router
from app.adapters.controllers.teacher import router as teacher_router
from app.adapters.controllers.dashboard import router as dashboard_router
from app.adapters.controllers.admin import router as admin_router
from app.adapters.controllers.training import router as training_router

__all__ = [
    "auth_router",
    "student_router",
    "teacher_router",
    "dashboard_router",
    "admin_router",
    "training_router",
]
