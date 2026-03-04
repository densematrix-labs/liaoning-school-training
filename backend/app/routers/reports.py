from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.report import ReportService
from app.schemas.auth import UserResponse
from app.schemas.report import DiagnosticReportResponse, GenerateReportRequest

router = APIRouter(prefix="/api/v1/reports", tags=["诊断报告"])


@router.post("/generate", response_model=DiagnosticReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成诊断报告"""
    # Check permission
    if current_user.role == "student":
        if request.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="无权访问")
    elif current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = ReportService(db)
    
    try:
        return await service.generate_report(
            student_id=request.student_id,
            report_type=request.report_type,
            score_id=request.score_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[DiagnosticReportResponse])
async def get_my_reports(
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前学生的诊断报告列表"""
    if current_user.role != "student" or not current_user.student_id:
        raise HTTPException(status_code=403, detail="仅学生可访问")
    
    service = ReportService(db)
    return await service.get_student_reports(current_user.student_id, limit)


@router.get("/student/{student_id}", response_model=List[DiagnosticReportResponse])
async def get_student_reports(
    student_id: str,
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定学生的诊断报告列表（教师/管理员）"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    service = ReportService(db)
    return await service.get_student_reports(student_id, limit)


@router.get("/{report_id}", response_model=DiagnosticReportResponse)
async def get_report(
    report_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报告详情"""
    service = ReportService(db)
    result = await service.get_report(report_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    # Check permission
    if current_user.role == "student":
        if result.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="无权访问")
    
    return result
