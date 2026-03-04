"""
报告相关 Schema
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class EnvCheckRequest(BaseModel):
    room_id: str
    image_base64: str


class EnvCheckResponse(BaseModel):
    id: str
    passed: bool
    overall_score: int
    categories: Dict[str, Any]
    issues: List[str]
    summary: str


class GenerateReportRequest(BaseModel):
    student_id: str
    type: str = "single"  # single 或 periodic
    training_record_id: Optional[str] = None


class GenerateReportResponse(BaseModel):
    report_id: str
    content: str


class DiagnosticReportResponse(BaseModel):
    id: str
    student_id: str
    report_type: str
    title: str
    content: Optional[str]
    content_html: Optional[str]
    pdf_url: Optional[str]
    generated_at: Optional[str]
    
    class Config:
        from_attributes = True
