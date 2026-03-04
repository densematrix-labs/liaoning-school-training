from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


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
    distribution: List[int]  # [0-20%, 20-40%, 40-60%, 60-80%, 80-100%]


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
    class_ranking: List[ClassRanking]
    ability_distribution: List[AbilityDistributionItem]
    trend: List[TrendDataPoint]
    lab_status: List[LabStatusItem]
    updated_at: datetime


class StudentDashboardResponse(BaseModel):
    student_id: str
    student_name: str
    total_trainings: int
    average_score: float
    recent_scores: List[Dict]
    ability_summary: Dict[str, float]
    graduation_progress: float
    recent_reports: List[Dict]
