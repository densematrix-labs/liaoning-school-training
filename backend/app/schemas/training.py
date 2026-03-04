"""
实训相关 Schema
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class TrainingRecordResponse(BaseModel):
    id: str
    project_id: str
    project_name: str
    student_id: str
    total_score: float
    max_score: float
    passed: bool
    completed_at: Optional[str]
    
    class Config:
        from_attributes = True


class ScoreResponse(BaseModel):
    id: str
    student_id: str
    project_id: str
    total_score: float
    max_score: float
    passed: bool
    completed_at: Optional[str]
    
    class Config:
        from_attributes = True


class ScoreListResponse(BaseModel):
    scores: List[ScoreResponse]
    total: int
    page: int
    page_size: int


class ScoreDetailResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    project_id: str
    project_name: str
    total_score: float
    max_score: float
    passed: bool
    completed_at: Optional[str]
    steps: List[Dict[str, Any]]
    failed_abilities: List[str]
    env_check: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ClassScoreSummary(BaseModel):
    class_id: str
    class_name: str
    student_count: int
    average_score: float
    pass_rate: float
    score_distribution: List[Dict[str, Any]]


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
    ability_distribution: List[Dict[str, Any]]
    score_distribution: List[Dict[str, Any]]


class StudentDetailResponse(BaseModel):
    id: str
    student_no: str
    name: str
    class_name: str
    enrollment_year: int
    total_trainings: int
    average_score: float
    graduation_ready: bool
    ability_map: Dict[str, Any]
    training_history: List[Dict[str, Any]]


class TrainingProjectResponse(BaseModel):
    id: str
    name: str
    lab_name: Optional[str]
    duration: Optional[int]
    difficulty: Optional[str]
    step_count: int


class TrainingRoomResponse(BaseModel):
    id: str
    name: str
    location: Optional[str]
    capacity: Optional[int]
    status: str
    current_students: int
