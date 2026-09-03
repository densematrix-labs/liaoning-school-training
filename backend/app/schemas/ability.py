"""能力体系相关 Schema。"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SubAbilityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 0.25


class SubAbilityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[float] = None


class SubAbilityResponse(BaseModel):
    id: str
    major_ability_id: str
    name: str
    description: Optional[str] = None
    weight: float


class MajorAbilityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 0.25
    graduation_threshold: float = 0.6
    icon: Optional[str] = None
    display_order: float = 0


class MajorAbilityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[float] = None
    graduation_threshold: Optional[float] = None
    icon: Optional[str] = None
    display_order: Optional[float] = None


class MajorAbilityResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    weight: float
    graduation_threshold: float
    icon: Optional[str] = None
    display_order: float = 0
    sub_abilities: list[SubAbilityResponse] = Field(default_factory=list)


class AbilityMappingResponse(BaseModel):
    project_id: str
    project_name: str
    step_mappings: dict[str, Any]


class RadarDataPoint(BaseModel):
    ability_id: str
    ability_name: str
    name: Optional[str] = None
    score: float
    full_score: float = 100
    weight: float = 0
    threshold: float


class RadarDataResponse(BaseModel):
    data: list[RadarDataPoint]


class AbilityProfileResponse(BaseModel):
    id: Optional[str] = None
    student_id: str
    student_name: Optional[str] = None
    sub_abilities: dict[str, float]
    major_abilities: dict[str, float]
    radar_data: list[RadarDataPoint]
    graduation_ready: bool
    updated_at: Optional[datetime] = None
    strongest_ability: Optional[str] = None
    weakest_ability: Optional[str] = None
    improvement_suggestions: Optional[list[str]] = None
    total_score: float = 0
    weak_abilities: list[dict[str, Any]] = Field(default_factory=list)


class ClassAbilityDistribution(BaseModel):
    class_id: str
    class_name: str
    abilities: dict[str, Any] = Field(default_factory=dict)
    graduation_ready_count: int = 0
    total_students: int = 0
