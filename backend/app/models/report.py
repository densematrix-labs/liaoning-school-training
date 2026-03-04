from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class ReportType(str, enum.Enum):
    SINGLE = "single"  # Single training report
    PERIODIC = "periodic"  # Periodic summary report


class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False)
    report_type = Column(SQLEnum(ReportType), default=ReportType.SINGLE)
    title = Column(String(200))
    content = Column(Text)  # Markdown content
    content_html = Column(Text)  # Rendered HTML
    pdf_url = Column(String(500))
    score_id = Column(String(36), ForeignKey("scores.id"))  # For single report
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student")
    score = relationship("Score")
