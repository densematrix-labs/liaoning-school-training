"""大屏数据 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class RealtimeStats(BaseModel):
    active_students: int
    today_trainings: int
    average_score: float
    pass_rate: float


class ClassRanking(BaseModel):
    class_id: str
    class_name: str
    average_score: float
    training_count: int
    rank: int


class AbilityDistributionItem(BaseModel):
    ability_id: str
    ability_name: str
    avg: float
    distribution: list[int]


class TrendDataPoint(BaseModel):
    date: str
    training_count: int
    average_score: float
    pass_rate: float


class LabStatusItem(BaseModel):
    lab_id: str
    lab_name: str
    status: str
    current_students: int
    capacity: int


class DashboardResponse(BaseModel):
    realtime: RealtimeStats
    class_ranking: list[ClassRanking]
    ability_distribution: list[AbilityDistributionItem]
    trend: list[TrendDataPoint]
    lab_status: list[LabStatusItem]
    updated_at: datetime


class DashboardOverview(BaseModel):
    today_training_count: int
    today_training_sessions: int
    pass_rate: float
    in_training_count: int
    env_check_count: int
    env_check_passed: int
    total_students: int
    total_trainings: int
    current_time: str


class RealtimeActivity(BaseModel):
    id: str
    student_name: str
    student_id: str
    class_name: str
    project_name: str
    status: str
    score: float | None = None
    passed: bool | None = None
    timestamp: str | None = None


class AbilityDistribution(BaseModel):
    ability_id: str
    name: str
    average_score: float
    max_score: float
    min_score: float
    student_count: int


class TrainingTrend(BaseModel):
    date: str
    training_count: int
    student_count: int
    average_score: float


class ClassComparison(BaseModel):
    class_id: str
    class_name: str
    average_score: float
    student_count: int


class AlertInfo(BaseModel):
    type: str
    level: str
    message: str
    student_id: str | None = None
    student_name: str | None = None
    timestamp: str
