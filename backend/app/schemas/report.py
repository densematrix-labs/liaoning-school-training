"""诊断报告相关 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    student_id: str
    report_type: str = "single"
    score_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class DiagnosticReportResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    report_type: str
    score_id: Optional[str] = None
    title: str
    content: str
    content_html: Optional[str] = None
    pdf_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    report_reference: Optional[str] = None
    project_name: Optional[str] = None
    training_completed_at: Optional[datetime] = None
    score_total: Optional[float] = None
    score_max: Optional[float] = None
    score_percentage: Optional[float] = None
    class_id: Optional[str] = None
    class_name: Optional[str] = None
    record_reference: Optional[str] = None

    class Config:
        from_attributes = True


class ReportTaskResponse(BaseModel):
    id: str
    student_id: str
    score_id: Optional[str] = None
    report_type: str
    status: str
    report_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    report: Optional[DiagnosticReportResponse] = None
