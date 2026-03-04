from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class LabStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"


class Lab(Base):
    __tablename__ = "labs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    building = Column(String(100))
    floor = Column(Integer)
    capacity = Column(Integer)
    equipment = Column(JSON)  # List of equipment
    reference_image_url = Column(String(500))  # Standard state photo
    status = Column(SQLEnum(LabStatus), default=LabStatus.AVAILABLE)
    current_students = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    environment_checks = relationship("EnvironmentCheck", back_populates="lab")


class EnvironmentCheck(Base):
    __tablename__ = "environment_checks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False)
    lab_id = Column(String(36), ForeignKey("labs.id"), nullable=False)
    score_id = Column(String(36), ForeignKey("scores.id"))
    uploaded_image_url = Column(String(500))
    total_score = Column(Integer)
    details = Column(JSON)  # {category: {score: x, issues: [...]}}
    summary = Column(String(1000))
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student")
    lab = relationship("Lab", back_populates="environment_checks")
    score = relationship("Score")
