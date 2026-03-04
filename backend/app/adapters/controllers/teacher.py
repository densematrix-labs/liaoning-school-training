"""
教师端 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
import json
import io
import csv

from app.database import get_db
from app.models.user import User
from app.models.student import Student, Class
from app.models.training import TrainingRecord, Score, TrainingProject
from app.models.ability import AbilityProfile, MajorAbility
from app.adapters.controllers.auth import get_current_teacher
from app.schemas.training import (
    ClassResponse,
    ClassStatisticsResponse,
    StudentDetailResponse,
    ClassStudentResponse,
)

router = APIRouter()


@router.get("/me/classes", response_model=List[ClassResponse])
async def get_teacher_classes(
    teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """获取教师管理的班级"""
    result = await db.execute(
        select(Class).where(Class.teacher_id == teacher.id)
    )
    classes = result.scalars().all()
    
    class_list = []
    for cls in classes:
        # 统计学生数
        student_count = await db.execute(
            select(func.count(Student.id)).where(Student.class_id == cls.id)
        )
        count = student_count.scalar() or 0
        
        class_list.append(ClassResponse(
            id=cls.id,
            name=cls.name,
            year=cls.year,
            student_count=count
        ))
    
    return class_list


@router.get("/classes/{class_id}/students", response_model=List[ClassStudentResponse])
async def get_class_students(
    class_id: str,
    teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """获取班级学生列表"""
    # 验证教师权限
    class_result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = class_result.scalar_one_or_none()
    
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    # 管理员可以查看所有班级，教师只能查看自己的
    if teacher.role.value != "admin" and cls.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="无权访问此班级")
    
    # 获取学生列表
    result = await db.execute(
        select(Student).where(Student.class_id == class_id).order_by(Student.student_no)
    )
    students = result.scalars().all()
    
    student_list = []
    for stu in students:
        # 获取实训统计
        record_count = await db.execute(
            select(func.count(TrainingRecord.id)).where(TrainingRecord.student_id == stu.id)
        )
        training_count = record_count.scalar() or 0
        
        # 获取平均分
        avg_result = await db.execute(
            select(func.avg(Score.total_score)).where(Score.student_id == stu.id)
        )
        avg_score = avg_result.scalar() or 0
        
        # 获取能力画像
        profile_result = await db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id == stu.id)
        )
        profile = profile_result.scalar_one_or_none()
        
        student_list.append(ClassStudentResponse(
            id=stu.id,
            student_no=stu.student_no,
            name=stu.name,
            training_count=training_count,
            average_score=round(avg_score, 1),
            graduation_ready=profile.graduation_ready if profile else False
        ))
    
    return student_list


@router.get("/classes/{class_id}/statistics", response_model=ClassStatisticsResponse)
async def get_class_statistics(
    class_id: str,
    teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """获取班级统计数据"""
    # 验证权限
    class_result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = class_result.scalar_one_or_none()
    
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    if teacher.role.value != "admin" and cls.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="无权访问此班级")
    
    # 获取班级所有学生
    students_result = await db.execute(
        select(Student.id).where(Student.class_id == class_id)
    )
    student_ids = [s[0] for s in students_result.all()]
    
    if not student_ids:
        return ClassStatisticsResponse(
            class_id=class_id,
            class_name=cls.name,
            student_count=0,
            total_trainings=0,
            average_score=0,
            pass_rate=0,
            ability_distribution=[],
            score_distribution=[]
        )
    
    # 实训总数
    training_count = await db.execute(
        select(func.count(TrainingRecord.id)).where(TrainingRecord.student_id.in_(student_ids))
    )
    total_trainings = training_count.scalar() or 0
    
    # 平均分
    avg_result = await db.execute(
        select(func.avg(Score.total_score)).where(Score.student_id.in_(student_ids))
    )
    average_score = avg_result.scalar() or 0
    
    # 合格率
    pass_count = await db.execute(
        select(func.count(Score.id)).where(
            Score.student_id.in_(student_ids),
            Score.total_score >= 60
        )
    )
    passed = pass_count.scalar() or 0
    total_scores = await db.execute(
        select(func.count(Score.id)).where(Score.student_id.in_(student_ids))
    )
    total = total_scores.scalar() or 1
    pass_rate = round(passed / total * 100, 1)
    
    # 能力分布
    major_abilities_result = await db.execute(
        select(MajorAbility).order_by(MajorAbility.display_order)
    )
    major_abilities = major_abilities_result.scalars().all()
    
    ability_distribution = []
    for ma in major_abilities:
        # 计算该能力的班级平均分
        profiles_result = await db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id.in_(student_ids))
        )
        profiles = profiles_result.scalars().all()
        
        scores = [p.major_abilities.get(ma.id, 0) for p in profiles if p.major_abilities]
        avg_ability_score = sum(scores) / len(scores) if scores else 0
        
        ability_distribution.append({
            "ability_id": ma.id,
            "name": ma.name,
            "average_score": round(avg_ability_score, 1)
        })
    
    # 分数分布
    score_ranges = [
        (90, 100, "优秀"),
        (80, 89, "良好"),
        (70, 79, "中等"),
        (60, 69, "及格"),
        (0, 59, "不及格")
    ]
    
    score_distribution = []
    for low, high, label in score_ranges:
        count = await db.execute(
            select(func.count(Score.id)).where(
                Score.student_id.in_(student_ids),
                Score.total_score >= low,
                Score.total_score <= high
            )
        )
        score_distribution.append({
            "range": f"{low}-{high}",
            "label": label,
            "count": count.scalar() or 0
        })
    
    return ClassStatisticsResponse(
        class_id=class_id,
        class_name=cls.name,
        student_count=len(student_ids),
        total_trainings=total_trainings,
        average_score=round(average_score, 1),
        pass_rate=pass_rate,
        ability_distribution=ability_distribution,
        score_distribution=score_distribution
    )


@router.get("/students/{student_id}/details", response_model=StudentDetailResponse)
async def get_student_details(
    student_id: str,
    teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """获取学生详情"""
    # 获取学生
    student_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 验证权限
    class_result = await db.execute(
        select(Class).where(Class.id == student.class_id)
    )
    cls = class_result.scalar_one_or_none()
    
    if teacher.role.value != "admin" and cls and cls.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="无权查看此学生")
    
    # 获取实训记录
    records_result = await db.execute(
        select(TrainingRecord, Score, TrainingProject)
        .join(Score, Score.record_id == TrainingRecord.id, isouter=True)
        .join(TrainingProject, TrainingProject.id == TrainingRecord.project_id)
        .where(TrainingRecord.student_id == student_id)
        .order_by(TrainingRecord.completed_at.desc())
        .limit(10)
    )
    records = records_result.all()
    
    training_history = [
        {
            "id": record.id,
            "project_name": project.name,
            "score": score.total_score if score else 0,
            "passed": score.total_score >= 60 if score else False,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None
        }
        for record, score, project in records
    ]
    
    # 获取能力画像
    profile_result = await db.execute(
        select(AbilityProfile).where(AbilityProfile.student_id == student_id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # 获取统计
    record_count = await db.execute(
        select(func.count(TrainingRecord.id)).where(TrainingRecord.student_id == student_id)
    )
    total_trainings = record_count.scalar() or 0
    
    avg_result = await db.execute(
        select(func.avg(Score.total_score)).where(Score.student_id == student_id)
    )
    average_score = avg_result.scalar() or 0
    
    return StudentDetailResponse(
        id=student.id,
        student_no=student.student_no,
        name=student.name,
        class_name=cls.name if cls else "",
        enrollment_year=student.enrollment_year,
        total_trainings=total_trainings,
        average_score=round(average_score, 1),
        graduation_ready=profile.graduation_ready if profile else False,
        ability_map=profile.major_abilities if profile else {},
        training_history=training_history
    )


@router.get("/export/class/{class_id}")
async def export_class_data(
    class_id: str,
    teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """导出班级数据 CSV"""
    # 验证权限
    class_result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = class_result.scalar_one_or_none()
    
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    if teacher.role.value != "admin" and cls.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="无权导出此班级数据")
    
    # 获取学生数据
    students_result = await db.execute(
        select(Student).where(Student.class_id == class_id).order_by(Student.student_no)
    )
    students = students_result.scalars().all()
    
    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["学号", "姓名", "实训次数", "平均分", "是否达标"])
    
    for stu in students:
        record_count = await db.execute(
            select(func.count(TrainingRecord.id)).where(TrainingRecord.student_id == stu.id)
        )
        training_count = record_count.scalar() or 0
        
        avg_result = await db.execute(
            select(func.avg(Score.total_score)).where(Score.student_id == stu.id)
        )
        avg_score = avg_result.scalar() or 0
        
        profile_result = await db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id == stu.id)
        )
        profile = profile_result.scalar_one_or_none()
        
        writer.writerow([
            stu.student_no,
            stu.name,
            training_count,
            round(avg_score, 1),
            "是" if (profile and profile.graduation_ready) else "否"
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={cls.name}_data.csv"
        }
    )
