from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectRuleUpdate(BaseModel):
    steps: list[dict[str, Any]]
    ability_mapping: dict[str, list[str]] = Field(default_factory=dict)


class RecalculateRequest(BaseModel):
    score_id: str | None = None


class TeacherAssignmentRequest(BaseModel):
    teacher_id: str | None = None


class SyncExceptionResponse(BaseModel):
    id: str
    row_number: int
    source_record_id: str | None = None
    reason: str
    raw_data: dict[str, Any] | None = None


class SyncTaskResponse(BaseModel):
    id: str
    status: str
    read_count: int
    success_count: int
    skipped_count: int
    error_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exceptions: list[SyncExceptionResponse] = Field(default_factory=list)
    message: str = "Mock 同步任务已完成"
