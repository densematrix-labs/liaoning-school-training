from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TrainingProjectResponse(BaseModel):
    id: str
    name: str
    major_id: str
    lab_id: Optional[str] = None
    lab_name: Optional[str] = None
    duration: Optional[int] = None
    max_score: float
    steps: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True


class TrainingRecordResponse(BaseModel):
    id: str
    student_id: str
    project_id: str
    project_name: Optional[str] = None
    steps_data: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StepScoreDetail(BaseModel):
    step_id: str
    step_name: str
    passed: bool
    score: float
    max_score: float
    deduction: Optional[float] = None
    reason: Optional[str] = None
    related_abilities: Optional[List[str]] = None


class ScoreResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    project_id: str
    project_name: Optional[str] = None
    total_score: float
    max_score: float
    percentage: Optional[float] = None
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class ScoreDetailResponse(ScoreResponse):
    details: Optional[List[StepScoreDetail]] = None
    failed_abilities: Optional[List[str]] = None
    environment_check: Optional[Dict[str, Any]] = None


class ScoreListResponse(BaseModel):
    scores: List[ScoreResponse]
    total: int
    page: int
    page_size: int
    average_score: Optional[float] = None


class ClassScoreSummary(BaseModel):
    class_id: str
    class_name: str
    student_count: int
    average_score: float
    pass_rate: float
    training_count: int
