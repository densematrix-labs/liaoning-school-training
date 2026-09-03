"""认证相关 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str
    student_id: Optional[str] = None
    student_no: Optional[str] = None
    class_name: Optional[str] = None
    major_name: Optional[str] = None
    classes: list[dict[str, str]] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
