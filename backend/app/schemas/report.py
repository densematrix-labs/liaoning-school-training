"""诊断报告相关 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    student_id: str
    report_type: str = "single"
    score_id: Optional[str] = None


class DiagnosticReportResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    report_type: str
    title: str
    content: str
    content_html: Optional[str] = None
    pdf_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    model: Optional[str] = None
    source: str = "llm_proxy"

    class Config:
        from_attributes = True
