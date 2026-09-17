from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import csv
import io

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.score import ScoreService
from app.schemas.auth import UserResponse
from app.schemas.training import ScoreListResponse, ScoreDetailResponse, ClassScoreSummary
from app.models.training import TrainingProject
from sqlalchemy import select
from app.routers.permissions import require_class_access, require_student_access

router = APIRouter(prefix="/api/v1/scores", tags=["成绩管理"])


@router.get("/projects")
async def get_projects(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(TrainingProject).order_by(TrainingProject.name))).scalars().all()
    return [{"id": item.id, "name": item.name} for item in rows]


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
    await require_student_access(current_user, student_id, db)
    
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
    student_id: Optional[str] = None,
    project_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级成绩列表"""
    await require_class_access(current_user, class_id, db)
    
    service = ScoreService(db)
    return await service.get_class_scores(
        class_id=class_id,
        page=page,
        page_size=page_size,
        student_id=student_id,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/class/{class_id}/summary", response_model=ClassScoreSummary)
async def get_class_summary(
    class_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级成绩汇总"""
    await require_class_access(current_user, class_id, db)
    
    service = ScoreService(db)
    return await service.get_class_summary(class_id)


@router.get("/class/{class_id}/export.csv")
async def export_class_scores(
    class_id: str,
    student_id: Optional[str] = None,
    project_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_class_access(current_user, class_id, db)
    data = await ScoreService(db).get_class_scores(
        class_id=class_id,
        page=1,
        page_size=200,
        student_id=student_id,
        project_id=project_id,
        date_from=date_from,
        date_to=date_to,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["学生", "实训项目", "成绩", "满分", "完成时间"])
    for item in data.scores:
        writer.writerow([item.student_name or item.student_id, item.project_name or item.project_id, item.total_score, item.max_score, item.calculated_at.isoformat() if item.calculated_at else ""])
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="class-{class_id}-scores.csv"'},
    )


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
    await require_student_access(current_user, result.student_id, db)
    
    return result
