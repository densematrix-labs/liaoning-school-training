from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SubAbilityResponse(BaseModel):
    id: str
    major_ability_id: str
    name: str
    description: Optional[str] = None
    weight: float
    score: Optional[float] = None  # When included in profile
    
    class Config:
        from_attributes = True


class MajorAbilityResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    weight: float
    graduation_threshold: float
    icon: Optional[str] = None
    score: Optional[float] = None  # When included in profile
    sub_abilities: Optional[List[SubAbilityResponse]] = None
    
    class Config:
        from_attributes = True


class RadarDataPoint(BaseModel):
    ability_id: str
    ability_name: str
    score: float
    full_score: float = 100.0
    threshold: float = 60.0


class RadarDataResponse(BaseModel):
    student_id: str
    student_name: str
    data: List[RadarDataPoint]
    updated_at: datetime


class AbilityProfileResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    major_abilities: Dict[str, float]  # {ability_id: score}
    sub_abilities: Dict[str, float]  # {ability_id: score}
    graduation_ready: bool
    radar_data: List[RadarDataPoint]
    updated_at: datetime
    
    # Additional insights
    strongest_ability: Optional[str] = None
    weakest_ability: Optional[str] = None
    improvement_suggestions: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class ClassAbilityDistribution(BaseModel):
    class_id: str
    class_name: str
    abilities: Dict[str, Dict[str, float]]  # {ability_id: {avg: x, distribution: [...]}}
    graduation_ready_count: int
    total_students: int
