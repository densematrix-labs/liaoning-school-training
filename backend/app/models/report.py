from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


LEGACY_GENERIC_REPORT_TITLES = frozenset({"单次实训诊断", "单次实训诊断报告"})


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

    @validates("title")
    def reject_legacy_generic_title(self, _key: str, value: str | None) -> str | None:
        """Keep future reports distinguishable while legacy rows remain readable."""
        if value and value.strip() in LEGACY_GENERIC_REPORT_TITLES:
            raise ValueError("诊断报告标题必须包含可识别的实训信息")
        return value
