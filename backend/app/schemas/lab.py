"""
实训室相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class LabCreate(BaseModel):
    name: str
    building: Optional[str] = None
    floor: Optional[int] = None
    capacity: Optional[int] = None
    equipment: Optional[List[str]] = None
    reference_image_url: Optional[str] = None


class LabUpdate(BaseModel):
    name: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[int] = None
    capacity: Optional[int] = None
    equipment: Optional[List[str]] = None
    reference_image_url: Optional[str] = None


class LabResponse(BaseModel):
    id: str
    name: str
    building: Optional[str] = None
    floor: Optional[int] = None
    capacity: Optional[int] = None
    equipment: List[str] = []
    reference_image_url: Optional[str] = None
    status: str
    current_students: int

    class Config:
        from_attributes = True


class EnvironmentCheckRequest(BaseModel):
    student_id: str
    lab_id: str
    image_base64: str
    score_id: Optional[str] = None


class CategoryScore(BaseModel):
    score: int
    max_score: int
    issues: List[str]


class EnvironmentCheckResponse(BaseModel):
    id: str
    student_id: str
    lab_id: str
    lab_name: Optional[str] = None
    total_score: int
    max_score: int = 100
    details: dict
    summary: str
    suggestions: List[str] = Field(default_factory=list)
    checked_at: Optional[datetime] = None
    uploaded_image_url: Optional[str] = None
    reference_image_url: Optional[str] = None
    review_status: Optional[str] = None
    reviewed_details: Optional[dict] = None
    reviewed_summary: Optional[str] = None
    review_note: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class EnvironmentReviewRequest(BaseModel):
    status: str
    reviewed_details: Optional[dict] = None
    reviewed_summary: Optional[str] = None
    note: Optional[str] = None


class EnvironmentTaskResponse(BaseModel):
    id: str
    student_id: str
    lab_id: str
    score_id: Optional[str] = None
    status: str
    check_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[EnvironmentCheckResponse] = None
