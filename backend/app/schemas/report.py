from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GenerateReportRequest(BaseModel):
    student_id: str
    report_type: str = "single"  # single or periodic
    score_id: Optional[str] = None  # For single report, specify which score


class DiagnosticReportResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    report_type: str
    title: str
    content: str  # Markdown
    content_html: Optional[str] = None
    pdf_url: Optional[str] = None
    generated_at: datetime
    
    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    reports: List[DiagnosticReportResponse]
    total: int


class BatchReportRequest(BaseModel):
    class_id: str
    report_type: str = "periodic"


class BatchReportResponse(BaseModel):
    total_students: int
    generated_count: int
    failed_count: int
    reports: List[DiagnosticReportResponse]
