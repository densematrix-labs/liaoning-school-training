from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.score import ScoreService
from app.schemas.auth import UserResponse
from app.schemas.training import ScoreListResponse, ScoreDetailResponse, ClassScoreSummary

router = APIRouter(prefix="/api/v1/scores", tags=["成绩管理"])


@router.get("/", response_model=ScoreListResponse)
async def get_scores(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前学生的成绩列表"""
    if current_user.role != "student" or not current_user.student_id:
        raise HTTPException(status_code=403, detail="仅学生可访问")
    
    service = ScoreService(db)
    return await service.get_student_scores(
        student_id=current_user.student_id,
        page=page,
        page_size=page_size,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/student/{student_id}", response_model=ScoreListResponse)
async def get_student_scores(
    student_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定学生的成绩列表（教师/管理员）"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = ScoreService(db)
    return await service.get_student_scores(
        student_id=student_id,
        page=page,
        page_size=page_size,
    )


@router.get("/class/{class_id}", response_model=ScoreListResponse)
async def get_class_scores(
    class_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级成绩列表"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = ScoreService(db)
    return await service.get_class_scores(
        class_id=class_id,
        page=page,
        page_size=page_size,
    )


@router.get("/class/{class_id}/summary", response_model=ClassScoreSummary)
async def get_class_summary(
    class_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级成绩汇总"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = ScoreService(db)
    return await service.get_class_summary(class_id)


@router.get("/{score_id}", response_model=ScoreDetailResponse)
async def get_score_detail(
    score_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取成绩详情"""
    service = ScoreService(db)
    result = await service.get_score_detail(score_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="成绩不存在")
    
    # Check permission
    if current_user.role == "student":
        if result.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="无权访问")
    
    return result
