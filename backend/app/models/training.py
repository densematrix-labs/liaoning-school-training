from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class TrainingProject(Base):
    __tablename__ = "training_projects"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    major_id = Column(String(36), ForeignKey("majors.id"), nullable=False)
    lab_id = Column(String(36), ForeignKey("labs.id"))
    duration = Column(Integer)  # minutes
    max_score = Column(Float, default=100.0)
    steps = Column(JSON)  # List of step definitions
    scoring_rules = Column(JSON)  # Scoring rules
    ability_mapping = Column(JSON)  # Step to ability mapping
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    major = relationship("Major")
    lab = relationship("Lab")
    records = relationship("TrainingRecord", back_populates="project")


class TrainingRecord(Base):
    __tablename__ = "training_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = Column(String(100), unique=True)  # From school's MySQL
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False)
    project_id = Column(String(36), ForeignKey("training_projects.id"), nullable=False)
    steps_data = Column(JSON)  # Each step's completion status
    completed_at = Column(DateTime(timezone=True))
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student")
    project = relationship("TrainingProject", back_populates="records")
    score = relationship("Score", back_populates="record", uselist=False)


class Score(Base):
    __tablename__ = "scores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("training_projects.id"), nullable=False, index=True)
    record_id = Column(String(36), ForeignKey("training_records.id"), unique=True)
    total_score = Column(Float, nullable=False)
    max_score = Column(Float, default=100.0)
    details = Column(JSON)  # Each step's score details
    failed_abilities = Column(JSON)  # List of failed ability IDs
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student")
    project = relationship("TrainingProject")
    record = relationship("TrainingRecord", back_populates="score")
