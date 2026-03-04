from app.schemas.auth import Token, TokenData, LoginRequest, UserResponse
from app.schemas.student import StudentResponse, ClassResponse, MajorResponse
from app.schemas.training import (
    TrainingProjectResponse,
    TrainingRecordResponse,
    ScoreResponse,
    ScoreListResponse,
    ScoreDetailResponse,
)
from app.schemas.ability import (
    MajorAbilityResponse,
    SubAbilityResponse,
    AbilityProfileResponse,
    RadarDataResponse,
)
from app.schemas.lab import LabResponse, EnvironmentCheckRequest, EnvironmentCheckResponse
from app.schemas.report import DiagnosticReportResponse, GenerateReportRequest
from app.schemas.dashboard import DashboardResponse

__all__ = [
    "Token",
    "TokenData",
    "LoginRequest",
    "UserResponse",
    "StudentResponse",
    "ClassResponse",
    "MajorResponse",
    "TrainingProjectResponse",
    "TrainingRecordResponse",
    "ScoreResponse",
    "ScoreListResponse",
    "ScoreDetailResponse",
    "MajorAbilityResponse",
    "SubAbilityResponse",
    "AbilityProfileResponse",
    "RadarDataResponse",
    "LabResponse",
    "EnvironmentCheckRequest",
    "EnvironmentCheckResponse",
    "DiagnosticReportResponse",
    "GenerateReportRequest",
    "DashboardResponse",
]
