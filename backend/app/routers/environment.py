from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.environment import EnvironmentCheckService
from app.schemas.auth import UserResponse
from app.schemas.lab import EnvironmentCheckRequest, EnvironmentCheckResponse, LabResponse
from app.models.lab import Lab
from app.routers.permissions import require_student_access

router = APIRouter(prefix="/api/v1/environment", tags=["环境检查"])


@router.get("/labs", response_model=List[LabResponse])
async def get_labs(
    db: AsyncSession = Depends(get_db),
):
    """获取所有实训室"""
    result = await db.execute(select(Lab))
    labs = result.scalars().all()
    
    return [
        LabResponse(
            id=lab.id,
            name=lab.name,
            building=lab.building,
            floor=lab.floor,
            capacity=lab.capacity,
            equipment=lab.equipment,
            reference_image_url=lab.reference_image_url,
            status=lab.status.value,
            current_students=lab.current_students or 0,
        )
        for lab in labs
    ]


@router.get("/labs/{lab_id}", response_model=LabResponse)
async def get_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取实训室详情"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail="实训室不存在")
    
    return LabResponse(
        id=lab.id,
        name=lab.name,
        building=lab.building,
        floor=lab.floor,
        capacity=lab.capacity,
        equipment=lab.equipment,
        reference_image_url=lab.reference_image_url,
        status=lab.status.value,
        current_students=lab.current_students or 0,
    )


@router.post("/check", response_model=EnvironmentCheckResponse)
async def check_environment(
    request: EnvironmentCheckRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传照片进行环境检查"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="仅教师和管理员可执行环境检查")

    await require_student_access(current_user, request.student_id, db)
    
    service = EnvironmentCheckService(db)
    
    try:
        return await service.check_environment(
            student_id=request.student_id,
            lab_id=request.lab_id,
            image_base64=request.image_base64,
            score_id=request.score_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history/{student_id}", response_model=List[EnvironmentCheckResponse])
async def get_student_check_history(
    student_id: str,
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定学生的环境检查历史（教师/管理员）"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="仅教师和管理员可访问")

    await require_student_access(current_user, student_id, db)
    
    service = EnvironmentCheckService(db)
    return await service.get_student_history(student_id, limit)
