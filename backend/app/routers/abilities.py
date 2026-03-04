from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.ability import AbilityService
from app.schemas.auth import UserResponse
from app.schemas.ability import AbilityProfileResponse, MajorAbilityResponse, ClassAbilityDistribution

router = APIRouter(prefix="/api/v1/abilities", tags=["能力图谱"])


@router.get("/schema", response_model=List[MajorAbilityResponse])
async def get_ability_schema(
    db: AsyncSession = Depends(get_db),
):
    """获取能力体系结构"""
    service = AbilityService(db)
    return await service.get_all_abilities()


@router.get("/profile", response_model=AbilityProfileResponse)
async def get_my_profile(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前学生的能力图谱"""
    if current_user.role != "student" or not current_user.student_id:
        raise HTTPException(status_code=403, detail="仅学生可访问")
    
    service = AbilityService(db)
    result = await service.get_student_profile(current_user.student_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="暂无能力数据")
    
    return result


@router.get("/student/{student_id}", response_model=AbilityProfileResponse)
async def get_student_profile(
    student_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定学生的能力图谱（教师/管理员）"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = AbilityService(db)
    result = await service.get_student_profile(student_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="暂无能力数据")
    
    return result


@router.get("/class/{class_id}", response_model=ClassAbilityDistribution)
async def get_class_distribution(
    class_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级能力分布"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = AbilityService(db)
    return await service.get_class_distribution(class_id)
