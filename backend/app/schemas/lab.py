"""
实训室相关 Schema
"""
from pydantic import BaseModel
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
    building: Optional[str]
    floor: Optional[int]
    capacity: Optional[int]
    equipment: List[str]
    reference_image_url: Optional[str]
    status: str
    current_students: int

    class Config:
        from_attributes = True


class EnvironmentCheckRequest(BaseModel):
    lab_id: str
    image_base64: str
    score_id: Optional[str] = None


class CategoryScore(BaseModel):
    score: int
    issues: List[str]


class EnvironmentCheckResponse(BaseModel):
    total_score: int
    categories: dict
    summary: str
    passed: bool
