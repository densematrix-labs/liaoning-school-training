"""
能力相关 Schema
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


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
    description: Optional[str]
    weight: float

    class Config:
        from_attributes = True


class MajorAbilityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 0.25
    graduation_threshold: float = 0.6
    icon: Optional[str] = None
    display_order: Optional[float] = 0


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
    description: Optional[str]
    weight: float
    graduation_threshold: float
    icon: Optional[str]
    display_order: float
    sub_abilities: List[SubAbilityResponse]

    class Config:
        from_attributes = True


class AbilityMappingResponse(BaseModel):
    project_id: str
    project_name: str
    step_mappings: Dict[str, Any]
