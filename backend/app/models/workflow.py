import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportTask(Base):
    __tablename__ = "report_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False, index=True)
    score_id = Column(String(36), ForeignKey("scores.id"), nullable=True)
    report_type = Column(String(20), nullable=False, default="single")
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    report_id = Column(String(36), ForeignKey("diagnostic_reports.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class EnvironmentReview(Base):
    __tablename__ = "environment_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    check_id = Column(String(36), ForeignKey("environment_checks.id"), unique=True, nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False)
    reviewed_details = Column(JSON, nullable=True)
    reviewed_summary = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EnvironmentTask(Base):
    __tablename__ = "environment_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False, index=True)
    lab_id = Column(String(36), ForeignKey("labs.id"), nullable=False)
    score_id = Column(String(36), ForeignKey("scores.id"), nullable=True)
    image_data = Column(Text, nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    check_id = Column(String(36), ForeignKey("environment_checks.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class MockSyncTask(Base):
    __tablename__ = "mock_sync_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.COMPLETED)
    read_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), server_default=func.now())


class MockSyncException(Base):
    __tablename__ = "mock_sync_exceptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("mock_sync_tasks.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    source_record_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    raw_data = Column(JSON, nullable=True)
