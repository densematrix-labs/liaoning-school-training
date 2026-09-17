from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from collections import defaultdict
from datetime import datetime

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.ability import AbilityService
from app.schemas.auth import UserResponse
from app.schemas.ability import AbilityProfileResponse, MajorAbilityResponse, ClassAbilityDistribution
from app.routers.permissions import require_class_access, require_student_access
from app.models.ability import MajorAbility, SubAbility
from app.models.training import Score, TrainingProject

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
    await require_student_access(current_user, student_id, db)
    
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
    await require_class_access(current_user, class_id, db)
    
    service = AbilityService(db)
    return await service.get_class_distribution(class_id)


@router.get("/student/{student_id}/trend")
async def get_ability_trend(
    student_id: str,
    project_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_student_access(current_user, student_id, db)
    query = select(Score, TrainingProject).join(TrainingProject, TrainingProject.id == Score.project_id).where(Score.student_id == student_id)
    if project_id:
        query = query.where(Score.project_id == project_id)
    if date_from:
        query = query.where(Score.calculated_at >= date_from)
    if date_to:
        query = query.where(Score.calculated_at <= date_to)
    rows = (await db.execute(query.order_by(Score.calculated_at))).all()
    abilities = (await db.execute(select(MajorAbility).order_by(MajorAbility.display_order))).scalars().all()
    subs = (await db.execute(select(SubAbility))).scalars().all()
    sub_to_major = {item.id: item.major_ability_id for item in subs}
    cumulative: dict[str, list[float]] = defaultdict(list)
    points = []
    for score, project in rows:
        mapping = project.ability_mapping or {}
        for step_id, detail in (score.details or {}).items():
            maximum = float(detail.get("max_score", 0) or 0)
            value = float(detail.get("score", 0) or 0) / maximum if maximum else 0
            for sub_id in mapping.get(str(step_id)) or detail.get("related_abilities", []):
                cumulative[sub_to_major.get(str(sub_id), str(sub_id))].append(value)
        points.append({
            "date": score.calculated_at,
            "score_id": score.id,
            "project_id": score.project_id,
            "project_name": project.name,
            "abilities": {item.id: round(sum(cumulative[item.id]) / len(cumulative[item.id]) * 100, 1) if cumulative[item.id] else 0 for item in abilities},
        })
    return {"abilities": [{"id": item.id, "name": item.name} for item in abilities], "points": points}
