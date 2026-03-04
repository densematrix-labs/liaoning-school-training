"""
学生端 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.student import Student
from app.models.training import TrainingRecord, Score, TrainingProject
from app.models.ability import AbilityProfile, MajorAbility, SubAbility
from app.models.report import DiagnosticReport
from app.models.lab import EnvironmentCheck
from app.adapters.controllers.auth import get_current_student
from app.schemas.student import (
    StudentProfileResponse,
    TrainingRecordResponse,
    TrainingRecordDetailResponse,
    AbilityMapResponse,
    ReportListResponse,
    ReportDetailResponse,
    GraduationProgressResponse,
)

router = APIRouter()


@router.get("/me", response_model=StudentProfileResponse)
async def get_student_profile(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """获取当前学生信息"""
    # 获取实训统计
    record_count = await db.execute(
        select(func.count(TrainingRecord.id)).where(TrainingRecord.student_id == student.id)
    )
    total_trainings = record_count.scalar() or 0
    
    # 获取平均分
    avg_score = await db.execute(
        select(func.avg(Score.total_score)).where(Score.student_id == student.id)
    )
    average_score = avg_score.scalar() or 0
    
    return StudentProfileResponse(
        id=student.id,
        student_no=student.student_no,
        name=student.name,
        class_name=student.class_.name if student.class_ else "",
        major_name=student.major.name if student.major else "",
        enrollment_year=student.enrollment_year,
        total_trainings=total_trainings,
        average_score=round(average_score, 1)
    )


@router.get("/me/training-records", response_model=List[TrainingRecordResponse])
async def get_training_records(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = None
):
    """获取实训记录列表"""
    query = (
        select(TrainingRecord, Score, TrainingProject)
        .join(Score, Score.record_id == TrainingRecord.id, isouter=True)
        .join(TrainingProject, TrainingProject.id == TrainingRecord.project_id)
        .where(TrainingRecord.student_id == student.id)
        .order_by(TrainingRecord.completed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    if project_id:
        query = query.where(TrainingRecord.project_id == project_id)
    
    result = await db.execute(query)
    records = result.all()
    
    return [
        TrainingRecordResponse(
            id=record.id,
            project_name=project.name,
            project_id=project.id,
            total_score=score.total_score if score else 0,
            passed=score.total_score >= 60 if score else False,
            completed_at=record.completed_at.isoformat() if record.completed_at else None,
            duration_minutes=project.duration
        )
        for record, score, project in records
    ]


@router.get("/me/training-records/{record_id}", response_model=TrainingRecordDetailResponse)
async def get_training_record_detail(
    record_id: str,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """获取单次实训详情"""
    result = await db.execute(
        select(TrainingRecord, Score, TrainingProject)
        .join(Score, Score.record_id == TrainingRecord.id, isouter=True)
        .join(TrainingProject, TrainingProject.id == TrainingRecord.project_id)
        .where(TrainingRecord.id == record_id)
        .where(TrainingRecord.student_id == student.id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="实训记录不存在")
    
    record, score, project = row
    
    # 获取环境检查结果
    env_check_result = await db.execute(
        select(EnvironmentCheck).where(EnvironmentCheck.score_id == score.id if score else None)
    )
    env_check = env_check_result.scalar_one_or_none()
    
    # 构建步骤详情
    steps_data = record.steps_data or []
    project_steps = project.steps or []
    
    step_details = []
    for i, step in enumerate(project_steps):
        step_result = steps_data[i] if i < len(steps_data) else {}
        step_details.append({
            "sequence": step.get("sequence", i + 1),
            "name": step.get("name", ""),
            "description": step.get("description", ""),
            "passed": step_result.get("passed", False),
            "score": step_result.get("score", 0),
            "ability_names": step.get("ability_names", [])
        })
    
    return TrainingRecordDetailResponse(
        id=record.id,
        project_name=project.name,
        project_id=project.id,
        total_score=score.total_score if score else 0,
        max_score=score.max_score if score else 100,
        passed=score.total_score >= 60 if score else False,
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
        duration_minutes=project.duration,
        steps=step_details,
        failed_abilities=score.failed_abilities if score else [],
        env_check={
            "passed": env_check.total_score >= 60 if env_check else None,
            "score": env_check.total_score if env_check else None,
            "summary": env_check.summary if env_check else None
        } if env_check else None
    )


@router.get("/me/ability-map", response_model=AbilityMapResponse)
async def get_ability_map(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """获取能力图谱"""
    # 获取能力画像
    profile_result = await db.execute(
        select(AbilityProfile).where(AbilityProfile.student_id == student.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # 获取所有大类能力
    major_abilities_result = await db.execute(
        select(MajorAbility).order_by(MajorAbility.display_order)
    )
    major_abilities = major_abilities_result.scalars().all()
    
    radar_data = []
    for ma in major_abilities:
        score = 0
        if profile and profile.major_abilities:
            score = profile.major_abilities.get(ma.id, 0)
        radar_data.append({
            "ability_id": ma.id,
            "name": ma.name,
            "score": round(score, 1),
            "weight": ma.weight,
            "threshold": ma.graduation_threshold * 100
        })
    
    # 计算总体进度
    total_score = sum(item["score"] * item["weight"] for item in radar_data) if radar_data else 0
    
    # 找出薄弱能力
    weak_abilities = [
        item for item in radar_data 
        if item["score"] < item["threshold"]
    ]
    
    return AbilityMapResponse(
        radar_data=radar_data,
        total_score=round(total_score, 1),
        weak_abilities=weak_abilities,
        updated_at=profile.updated_at.isoformat() if profile and profile.updated_at else None
    )


@router.get("/me/reports", response_model=List[ReportListResponse])
async def get_reports(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """获取诊断报告列表"""
    result = await db.execute(
        select(DiagnosticReport)
        .where(DiagnosticReport.student_id == student.id)
        .order_by(DiagnosticReport.generated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    reports = result.scalars().all()
    
    return [
        ReportListResponse(
            id=report.id,
            title=report.title or "诊断报告",
            report_type=report.report_type.value,
            generated_at=report.generated_at.isoformat() if report.generated_at else None
        )
        for report in reports
    ]


@router.get("/me/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(
    report_id: str,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """获取报告详情"""
    result = await db.execute(
        select(DiagnosticReport)
        .where(DiagnosticReport.id == report_id)
        .where(DiagnosticReport.student_id == student.id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    return ReportDetailResponse(
        id=report.id,
        title=report.title or "诊断报告",
        report_type=report.report_type.value,
        content=report.content,
        content_html=report.content_html,
        pdf_url=report.pdf_url,
        generated_at=report.generated_at.isoformat() if report.generated_at else None
    )


@router.get("/me/graduation-progress", response_model=GraduationProgressResponse)
async def get_graduation_progress(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """获取毕业进度"""
    # 获取能力画像
    profile_result = await db.execute(
        select(AbilityProfile).where(AbilityProfile.student_id == student.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # 获取所有大类能力
    major_abilities_result = await db.execute(
        select(MajorAbility).order_by(MajorAbility.display_order)
    )
    major_abilities = major_abilities_result.scalars().all()
    
    ability_progress = []
    all_passed = True
    
    for ma in major_abilities:
        score = 0
        if profile and profile.major_abilities:
            score = profile.major_abilities.get(ma.id, 0)
        
        threshold = ma.graduation_threshold * 100
        passed = score >= threshold
        if not passed:
            all_passed = False
        
        ability_progress.append({
            "ability_id": ma.id,
            "name": ma.name,
            "current_score": round(score, 1),
            "required_score": threshold,
            "passed": passed,
            "progress_percent": min(100, round(score / threshold * 100, 1)) if threshold > 0 else 100
        })
    
    # 计算总进度
    total_progress = sum(item["progress_percent"] for item in ability_progress) / len(ability_progress) if ability_progress else 0
    
    return GraduationProgressResponse(
        total_progress=round(total_progress, 1),
        graduation_ready=all_passed,
        ability_progress=ability_progress,
        estimated_completion=None  # 可以根据历史数据预测
    )
