from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class MajorAbility(Base):
    __tablename__ = "major_abilities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    weight = Column(Float, default=0.25)
    graduation_threshold = Column(Float, default=0.6)
    icon = Column(String(50))
    display_order = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    sub_abilities = relationship("SubAbility", back_populates="major_ability")


class SubAbility(Base):
    __tablename__ = "sub_abilities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    major_ability_id = Column(String(36), ForeignKey("major_abilities.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    weight = Column(Float, default=0.25)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    major_ability = relationship("MajorAbility", back_populates="sub_abilities")


class AbilityProfile(Base):
    __tablename__ = "ability_profiles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id"), unique=True, nullable=False)
    sub_abilities = Column(JSON)  # {ability_id: score}
    major_abilities = Column(JSON)  # {ability_id: score}
    radar_data = Column(JSON)  # Pre-computed radar chart data
    graduation_ready = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    student = relationship("Student")
