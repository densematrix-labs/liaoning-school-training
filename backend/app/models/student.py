from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Major(Base):
    __tablename__ = "majors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    classes = relationship("Class", back_populates="major")
    students = relationship("Student", back_populates="major")


class Class(Base):
    __tablename__ = "classes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    major_id = Column(String(36), ForeignKey("majors.id"), nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id"))
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    major = relationship("Major", back_populates="classes")
    students = relationship("Student", back_populates="class_")
    teacher = relationship("User")


class Student(Base):
    __tablename__ = "students"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    student_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    major_id = Column(String(36), ForeignKey("majors.id"), nullable=False)
    class_id = Column(String(36), ForeignKey("classes.id"), nullable=False)
    enrollment_year = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
    major = relationship("Major", back_populates="students")
    class_ = relationship("Class", back_populates="students")
