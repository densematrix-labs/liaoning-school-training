from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LabResponse(BaseModel):
    id: str
    name: str
    building: Optional[str] = None
    floor: Optional[int] = None
    capacity: Optional[int] = None
    equipment: Optional[List[str]] = None
    reference_image_url: Optional[str] = None
    status: str
    current_students: int = 0
    
    class Config:
        from_attributes = True


class EnvironmentCheckRequest(BaseModel):
    lab_id: str
    image_base64: str  # Base64 encoded image
    score_id: Optional[str] = None  # Link to training score


class CategoryScore(BaseModel):
    score: int
    max_score: int
    issues: List[str]


class EnvironmentCheckResponse(BaseModel):
    id: str
    student_id: str
    lab_id: str
    lab_name: Optional[str] = None
    uploaded_image_url: Optional[str] = None
    total_score: int
    max_score: int = 100
    details: Dict[str, CategoryScore]
    summary: str
    checked_at: datetime
    
    class Config:
        from_attributes = True


class EnvironmentCheckHistoryResponse(BaseModel):
    checks: List[EnvironmentCheckResponse]
    total: int
    average_score: Optional[float] = None
