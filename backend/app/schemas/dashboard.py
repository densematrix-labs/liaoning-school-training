"""
大屏展示 Schema
"""
from pydantic import BaseModel
from typing import Optional


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
    status: str  # completed, in_progress
    score: Optional[float]
    passed: Optional[bool]
    timestamp: Optional[str]


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
    type: str  # ability_warning, consecutive_fail, env_check_fail
    level: str  # warning, danger
    message: str
    student_id: Optional[str]
    student_name: Optional[str]
    timestamp: str
