"""
大屏展示 API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta
import random

from app.database import get_db
from app.models.student import Student, Class
from app.models.training import TrainingRecord, Score, TrainingProject
from app.models.ability import AbilityProfile, MajorAbility
from app.models.lab import Lab, EnvironmentCheck
from app.schemas.dashboard import (
    DashboardOverview,
    RealtimeActivity,
    AbilityDistribution,
    TrainingTrend,
    ClassComparison,
    AlertInfo,
)

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """获取大屏概览数据"""
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # 今日实训人数
    today_trainings = await db.execute(
        select(func.count(func.distinct(TrainingRecord.student_id))).where(
            TrainingRecord.completed_at >= today_start
        )
    )
    today_count = today_trainings.scalar() or 0
    
    # 今日实训次数
    today_records = await db.execute(
        select(func.count(TrainingRecord.id)).where(
            TrainingRecord.completed_at >= today_start
        )
    )
    today_training_count = today_records.scalar() or 0
    
    # 今日合格率
    today_passed = await db.execute(
        select(func.count(Score.id)).where(
            Score.calculated_at >= today_start,
            Score.total_score >= 60
        )
    )
    passed_count = today_passed.scalar() or 0
    
    today_total = await db.execute(
        select(func.count(Score.id)).where(Score.calculated_at >= today_start)
    )
    total_count = today_total.scalar() or 1
    pass_rate = round(passed_count / total_count * 100, 1) if total_count > 0 else 0
    
    # 在训人数（模拟）
    in_training = random.randint(5, 15)
    
    # 今日环境检查
    today_env_checks = await db.execute(
        select(func.count(EnvironmentCheck.id)).where(
            EnvironmentCheck.checked_at >= today_start
        )
    )
    env_check_count = today_env_checks.scalar() or 0
    
    env_passed = await db.execute(
        select(func.count(EnvironmentCheck.id)).where(
            EnvironmentCheck.checked_at >= today_start,
            EnvironmentCheck.total_score >= 60
        )
    )
    env_passed_count = env_passed.scalar() or 0
    
    # 总学生数
    total_students = await db.execute(select(func.count(Student.id)))
    student_count = total_students.scalar() or 0
    
    # 总实训次数
    total_trainings = await db.execute(select(func.count(TrainingRecord.id)))
    training_total = total_trainings.scalar() or 0
    
    return DashboardOverview(
        today_training_count=today_count,
        today_training_sessions=today_training_count,
        pass_rate=pass_rate,
        in_training_count=in_training,
        env_check_count=env_check_count,
        env_check_passed=env_passed_count,
        total_students=student_count,
        total_trainings=training_total,
        current_time=datetime.now().isoformat()
    )


@router.get("/realtime", response_model=List[RealtimeActivity])
async def get_realtime_activities(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """获取实时实训动态"""
    # 获取最近的实训记录
    result = await db.execute(
        select(TrainingRecord, Student, TrainingProject, Score)
        .join(Student, Student.id == TrainingRecord.student_id)
        .join(TrainingProject, TrainingProject.id == TrainingRecord.project_id)
        .join(Score, Score.record_id == TrainingRecord.id, isouter=True)
        .order_by(TrainingRecord.completed_at.desc())
        .limit(limit)
    )
    records = result.all()
    
    activities = []
    for record, student, project, score in records:
        # 获取班级信息
        class_result = await db.execute(
            select(Class).where(Class.id == student.class_id)
        )
        cls = class_result.scalar_one_or_none()
        
        status = "completed" if record.completed_at else "in_progress"
        
        activities.append(RealtimeActivity(
            id=record.id,
            student_name=student.name,
            student_id=student.student_no,
            class_name=cls.name if cls else "",
            project_name=project.name,
            status=status,
            score=score.total_score if score else None,
            passed=score.total_score >= 60 if score else None,
            timestamp=record.completed_at.isoformat() if record.completed_at else None
        ))
    
    return activities


@router.get("/ability-distribution", response_model=List[AbilityDistribution])
async def get_ability_distribution(db: AsyncSession = Depends(get_db)):
    """获取能力分布统计"""
    # 获取所有大类能力
    major_abilities_result = await db.execute(
        select(MajorAbility).order_by(MajorAbility.display_order)
    )
    major_abilities = major_abilities_result.scalars().all()
    
    # 获取所有能力画像
    profiles_result = await db.execute(select(AbilityProfile))
    profiles = profiles_result.scalars().all()
    
    distribution = []
    for ma in major_abilities:
        scores = []
        for profile in profiles:
            if profile.major_abilities:
                score = profile.major_abilities.get(ma.id, 0)
                scores.append(score)
        
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0
        min_score = min(scores) if scores else 0
        
        distribution.append(AbilityDistribution(
            ability_id=ma.id,
            name=ma.name,
            average_score=round(avg_score, 1),
            max_score=round(max_score, 1),
            min_score=round(min_score, 1),
            student_count=len(scores)
        ))
    
    return distribution


@router.get("/training-trend", response_model=List[TrainingTrend])
async def get_training_trend(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """获取实训趋势数据"""
    trends = []
    today = datetime.now().date()
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        date_start = datetime.combine(date, datetime.min.time())
        date_end = datetime.combine(date, datetime.max.time())
        
        # 当日实训次数
        count_result = await db.execute(
            select(func.count(TrainingRecord.id)).where(
                TrainingRecord.completed_at >= date_start,
                TrainingRecord.completed_at <= date_end
            )
        )
        training_count = count_result.scalar() or 0
        
        # 当日实训人数
        student_count_result = await db.execute(
            select(func.count(func.distinct(TrainingRecord.student_id))).where(
                TrainingRecord.completed_at >= date_start,
                TrainingRecord.completed_at <= date_end
            )
        )
        student_count = student_count_result.scalar() or 0
        
        # 当日平均分
        avg_result = await db.execute(
            select(func.avg(Score.total_score)).where(
                Score.calculated_at >= date_start,
                Score.calculated_at <= date_end
            )
        )
        avg_score = avg_result.scalar() or 0
        
        trends.append(TrainingTrend(
            date=date.isoformat(),
            training_count=training_count,
            student_count=student_count,
            average_score=round(avg_score, 1)
        ))
    
    return trends


@router.get("/class-comparison", response_model=List[ClassComparison])
async def get_class_comparison(db: AsyncSession = Depends(get_db)):
    """获取班级能力对比"""
    # 获取所有班级
    classes_result = await db.execute(select(Class))
    classes = classes_result.scalars().all()
    
    comparisons = []
    for cls in classes:
        # 获取班级学生
        students_result = await db.execute(
            select(Student.id).where(Student.class_id == cls.id)
        )
        student_ids = [s[0] for s in students_result.all()]
        
        if not student_ids:
            continue
        
        # 获取班级能力画像
        profiles_result = await db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id.in_(student_ids))
        )
        profiles = profiles_result.scalars().all()
        
        # 计算班级平均能力分
        if profiles:
            all_scores = []
            for profile in profiles:
                if profile.major_abilities:
                    avg = sum(profile.major_abilities.values()) / len(profile.major_abilities)
                    all_scores.append(avg)
            
            class_avg = sum(all_scores) / len(all_scores) if all_scores else 0
        else:
            class_avg = 0
        
        comparisons.append(ClassComparison(
            class_id=cls.id,
            class_name=cls.name,
            average_score=round(class_avg, 1),
            student_count=len(student_ids)
        ))
    
    # 按平均分排序
    comparisons.sort(key=lambda x: x.average_score, reverse=True)
    
    return comparisons


@router.get("/alerts", response_model=List[AlertInfo])
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """获取预警信息"""
    alerts = []
    
    # 找出能力低于60%的学生
    profiles_result = await db.execute(select(AbilityProfile))
    profiles = profiles_result.scalars().all()
    
    for profile in profiles:
        if not profile.major_abilities:
            continue
        
        # 获取学生信息
        student_result = await db.execute(
            select(Student).where(Student.id == profile.student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student:
            continue
        
        # 检查是否有低于60分的能力
        for ability_id, score in profile.major_abilities.items():
            if score < 60:
                # 获取能力名称
                ability_result = await db.execute(
                    select(MajorAbility).where(MajorAbility.id == ability_id)
                )
                ability = ability_result.scalar_one_or_none()
                
                alerts.append(AlertInfo(
                    type="ability_warning",
                    level="warning",
                    message=f"{student.name} - {ability.name if ability else '某项能力'}低于60%",
                    student_id=student.id,
                    student_name=student.name,
                    timestamp=datetime.now().isoformat()
                ))
    
    # 找出连续3次未通过的学生
    students_result = await db.execute(select(Student))
    students = students_result.scalars().all()
    
    for student in students:
        # 获取最近3次实训
        recent_scores = await db.execute(
            select(Score)
            .where(Score.student_id == student.id)
            .order_by(Score.calculated_at.desc())
            .limit(3)
        )
        scores = recent_scores.scalars().all()
        
        if len(scores) >= 3 and all(s.total_score < 60 for s in scores):
            alerts.append(AlertInfo(
                type="consecutive_fail",
                level="danger",
                message=f"{student.name} - 连续3次实训未通过",
                student_id=student.id,
                student_name=student.name,
                timestamp=datetime.now().isoformat()
            ))
    
    # 限制返回数量并按时间排序
    alerts = alerts[:limit]
    
    return alerts
