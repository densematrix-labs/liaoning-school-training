from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str
    created_at: datetime
    
    # Student-specific fields (if role is student)
    student_id: Optional[str] = None
    student_no: Optional[str] = None
    class_name: Optional[str] = None
    major_name: Optional[str] = None
    
    # Teacher-specific fields (if role is teacher)
    classes: Optional[list] = None

    class Config:
        from_attributes = True
