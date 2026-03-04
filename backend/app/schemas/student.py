from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MajorResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ClassResponse(BaseModel):
    id: str
    name: str
    major_id: str
    major_name: Optional[str] = None
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    year: int
    student_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class StudentResponse(BaseModel):
    id: str
    student_no: str
    name: str
    major_id: str
    major_name: Optional[str] = None
    class_id: str
    class_name: Optional[str] = None
    enrollment_year: int
    
    class Config:
        from_attributes = True


class ClassStudentsResponse(BaseModel):
    class_info: ClassResponse
    students: List[StudentResponse]
    total: int
