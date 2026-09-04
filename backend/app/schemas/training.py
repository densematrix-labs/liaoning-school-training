"""成绩与实训相关 Schema。"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScoreResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    project_id: str
    project_name: Optional[str] = None
    total_score: float
    max_score: float
    percentage: float
    calculated_at: Optional[datetime] = None


class ScoreListResponse(BaseModel):
    scores: list[ScoreResponse]
    total: int
    page: int
    page_size: int
    average_score: Optional[float] = None


class StepScoreDetail(BaseModel):
    step_id: str
    step_name: str
    passed: bool
    score: float
    max_score: float
    deduction: Optional[float] = None
    reason: Optional[str] = None
    related_abilities: list[str] = Field(default_factory=list)
    related_ability_names: list[str] = Field(default_factory=list)
    source_status: Optional[str] = None
    applied_rule: dict[str, Any] = Field(default_factory=dict)


class ScoreDetailResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    project_id: str
    project_name: Optional[str] = None
    total_score: float
    max_score: float
    percentage: float
    calculated_at: Optional[datetime] = None
    details: list[StepScoreDetail] = Field(default_factory=list)
    failed_abilities: list[str] = Field(default_factory=list)
    class_name: Optional[str] = None
    record_id: Optional[str] = None
    source_record_id: Optional[str] = None
    source_completed_at: Optional[datetime] = None
    steps_total: float = 0
    reconciliation_ok: bool = False


class ClassScoreSummary(BaseModel):
    class_id: str
    class_name: str
    student_count: int
    average_score: float
    pass_rate: float
    training_count: int


class TrainingRecordResponse(BaseModel):
    id: str
    project_id: str
    project_name: str
    student_id: str
    total_score: float
    max_score: float
    passed: bool
    completed_at: Optional[datetime] = None


class ClassStudentResponse(BaseModel):
    id: str
    student_no: str
    name: str
    training_count: int
    average_score: float
    graduation_ready: bool


class ClassStatisticsResponse(BaseModel):
    class_id: str
    class_name: str
    student_count: int
    total_trainings: int
    average_score: float
    pass_rate: float
    ability_distribution: list[dict[str, Any]]
    score_distribution: list[dict[str, Any]]


class StudentDetailResponse(BaseModel):
    id: str
    student_no: str
    name: str
    class_name: str
    enrollment_year: int
    total_trainings: int
    average_score: float
    graduation_ready: bool
    ability_map: dict[str, Any]
    training_history: list[dict[str, Any]]


class TrainingProjectResponse(BaseModel):
    id: str
    name: str
    lab_name: Optional[str] = None
    duration: Optional[int] = None
    difficulty: Optional[str] = None
    step_count: int


class TrainingRoomResponse(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    capacity: Optional[int] = None
    status: str
    current_students: int
