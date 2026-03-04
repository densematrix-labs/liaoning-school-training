"""
学生端 Schema
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class StudentProfileResponse(BaseModel):
    id: str
    student_no: str
    name: str
    class_name: str
    major_name: str
    enrollment_year: int
    total_trainings: int
    average_score: float

    class Config:
        from_attributes = True


class TrainingRecordResponse(BaseModel):
    id: str
    project_name: str
    project_id: str
    total_score: float
    passed: bool
    completed_at: Optional[str]
    duration_minutes: Optional[int]


class StepDetail(BaseModel):
    sequence: int
    name: str
    description: str
    passed: bool
    score: float
    ability_names: List[str]


class EnvCheckResult(BaseModel):
    passed: Optional[bool]
    score: Optional[int]
    summary: Optional[str]


class TrainingRecordDetailResponse(BaseModel):
    id: str
    project_name: str
    project_id: str
    total_score: float
    max_score: float
    passed: bool
    completed_at: Optional[str]
    duration_minutes: Optional[int]
    steps: List[Dict[str, Any]]
    failed_abilities: Optional[List[str]]
    env_check: Optional[Dict[str, Any]]


class AbilityDataPoint(BaseModel):
    ability_id: str
    name: str
    score: float
    weight: float
    threshold: float


class AbilityMapResponse(BaseModel):
    radar_data: List[Dict[str, Any]]
    total_score: float
    weak_abilities: List[Dict[str, Any]]
    updated_at: Optional[str]


class ReportListResponse(BaseModel):
    id: str
    title: str
    report_type: str
    generated_at: Optional[str]


class ReportDetailResponse(BaseModel):
    id: str
    title: str
    report_type: str
    content: Optional[str]
    content_html: Optional[str]
    pdf_url: Optional[str]
    generated_at: Optional[str]


class AbilityProgressItem(BaseModel):
    ability_id: str
    name: str
    current_score: float
    required_score: float
    passed: bool
    progress_percent: float


class GraduationProgressResponse(BaseModel):
    total_progress: float
    graduation_ready: bool
    ability_progress: List[Dict[str, Any]]
    estimated_completion: Optional[str]
