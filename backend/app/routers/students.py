from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections import Counter, defaultdict
from typing import List

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.student import Student, Class, Major
from app.models.training import Score, TrainingProject
from app.models.ability import AbilityProfile, MajorAbility, SubAbility
from app.models.report import DiagnosticReport
from app.models.lab import EnvironmentCheck
from app.services.ability import AbilityService
from app.services.score import ScoreService
from app.schemas.auth import UserResponse
from app.schemas.student import StudentResponse, ClassResponse, MajorResponse
from app.routers.permissions import require_class_access, require_student_access

router = APIRouter(prefix="/api/v1/students", tags=["学生管理"])


@router.get("/majors", response_model=List[MajorResponse])
async def get_majors(
    db: AsyncSession = Depends(get_db),
):
    """获取所有专业"""
    result = await db.execute(select(Major))
    majors = result.scalars().all()
    
    return [
        MajorResponse(
            id=m.id,
            code=m.code,
            name=m.name,
            description=m.description,
        )
        for m in majors
    ]


@router.get("/classes", response_model=List[ClassResponse])
async def get_classes(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级列表"""
    if current_user.role == "teacher":
        # Get teacher's classes
        result = await db.execute(
            select(Class).where(Class.teacher_id == current_user.id)
        )
    elif current_user.role == "admin":
        result = await db.execute(select(Class))
    else:
        raise HTTPException(status_code=403, detail="无权访问")
    
    classes = result.scalars().all()
    
    responses = []
    for cls in classes:
        # Get major name
        major_result = await db.execute(
            select(Major).where(Major.id == cls.major_id)
        )
        major = major_result.scalar_one_or_none()
        
        # Count students
        count_result = await db.execute(
            select(Student).where(Student.class_id == cls.id)
        )
        students = count_result.scalars().all()
        
        responses.append(ClassResponse(
            id=cls.id,
            name=cls.name,
            major_id=cls.major_id,
            major_name=major.name if major else None,
            teacher_id=cls.teacher_id,
            year=cls.year,
            student_count=len(students),
        ))
    
    return responses


@router.get("/classes/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级详情"""
    await require_class_access(current_user, class_id, db)
    
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()
    
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    
    # Get major name
    major_result = await db.execute(
        select(Major).where(Major.id == cls.major_id)
    )
    major = major_result.scalar_one_or_none()
    
    # Count students
    count_result = await db.execute(
        select(Student).where(Student.class_id == cls.id)
    )
    students = count_result.scalars().all()
    
    return ClassResponse(
        id=cls.id,
        name=cls.name,
        major_id=cls.major_id,
        major_name=major.name if major else None,
        teacher_id=cls.teacher_id,
        year=cls.year,
        student_count=len(students),
    )


@router.get("/classes/{class_id}/students", response_model=List[StudentResponse])
async def get_class_students(
    class_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取班级学生列表"""
    await require_class_access(current_user, class_id, db)
    
    result = await db.execute(
        select(Student).where(Student.class_id == class_id)
    )
    students = result.scalars().all()
    
    responses = []
    for student in students:
        # Get major and class names
        major_result = await db.execute(
            select(Major).where(Major.id == student.major_id)
        )
        major = major_result.scalar_one_or_none()
        
        class_result = await db.execute(
            select(Class).where(Class.id == student.class_id)
        )
        cls = class_result.scalar_one_or_none()
        
        responses.append(StudentResponse(
            id=student.id,
            student_no=student.student_no,
            name=student.name,
            major_id=student.major_id,
            major_name=major.name if major else None,
            class_id=student.class_id,
            class_name=cls.name if cls else None,
            enrollment_year=student.enrollment_year,
        ))
    
    return responses


@router.get("/classes/{class_id}/overview")
async def get_class_overview(
    class_id: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_class_access(current_user, class_id, db)
    class_obj = (await db.execute(select(Class).where(Class.id == class_id))).scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="班级不存在")

    students = list((await db.execute(select(Student).where(Student.class_id == class_id))).scalars().all())
    student_ids = [item.id for item in students]
    query = select(Score).where(Score.student_id.in_(student_ids))
    if date_from:
        query = query.where(Score.calculated_at >= date_from)
    if date_to:
        query = query.where(Score.calculated_at <= date_to)
    scores = list((await db.execute(query)).scalars().all()) if student_ids else []

    scores_by_student: dict[str, list[Score]] = defaultdict(list)
    for score in scores:
        scores_by_student[score.student_id].append(score)

    abilities = list((await db.execute(select(MajorAbility).order_by(MajorAbility.display_order))).scalars().all())
    sub_abilities = list((await db.execute(select(SubAbility))).scalars().all())
    sub_by_major: dict[str, list[SubAbility]] = defaultdict(list)
    for sub in sub_abilities:
        sub_by_major[sub.major_ability_id].append(sub)
    project_ids = {item.project_id for item in scores}
    projects = list((await db.execute(select(TrainingProject).where(TrainingProject.id.in_(project_ids)))).scalars().all()) if project_ids else []
    project_map = {item.id: item for item in projects}
    profiles: list[dict] = []
    for student in students:
        sub_values: dict[str, list[float]] = defaultdict(list)
        for score in scores_by_student.get(student.id, []):
            project = project_map.get(score.project_id)
            mapping = project.ability_mapping or {} if project else {}
            for step_id, detail in (score.details or {}).items():
                max_score = float(detail.get("max_score", 0) or 0)
                normalized = float(detail.get("score", 0) or 0) / max_score if max_score else 0
                for ability_id in mapping.get(str(step_id)) or detail.get("related_abilities", []):
                    sub_values[str(ability_id)].append(normalized)
        if not sub_values:
            continue
        sub_average = {key: sum(values) / len(values) for key, values in sub_values.items()}
        major_average = {}
        ready = True
        for ability in abilities:
            weighted = [(sub_average[sub.id], sub.weight) for sub in sub_by_major[ability.id] if sub.id in sub_average]
            weight_total = sum(weight for _, weight in weighted)
            value = sum(value * weight for value, weight in weighted) / weight_total if weight_total else 0
            major_average[ability.id] = value
            ready = ready and value >= ability.graduation_threshold
        profiles.append({"student_id": student.id, "major_abilities": major_average, "graduation_ready": ready})

    ability_distribution = []
    weak_counter: Counter[str] = Counter()
    for ability in abilities:
        values = [float(profile["major_abilities"].get(ability.id, 0)) * 100 for profile in profiles]
        average = round(sum(values) / len(values), 1) if values else 0
        ability_distribution.append({"id": ability.id, "name": ability.name, "average": average})
        for profile in profiles:
            if float(profile["major_abilities"].get(ability.id, 0)) < ability.graduation_threshold:
                weak_counter[ability.name] += 1

    ranges = [(90, 101, "90-100"), (80, 90, "80-89"), (70, 80, "70-79"), (60, 70, "60-69"), (0, 60, "0-59")]
    percentages = [score.total_score / score.max_score * 100 if score.max_score else 0 for score in scores]
    score_distribution = [
        {"label": label, "count": sum(1 for value in percentages if low <= value < high)}
        for low, high, label in ranges
    ]
    student_rows = []
    profile_map = {item["student_id"]: item for item in profiles}
    for student in students:
        items = scores_by_student.get(student.id, [])
        values = [score.total_score / score.max_score * 100 if score.max_score else 0 for score in items]
        profile = profile_map.get(student.id)
        student_rows.append({
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "training_count": len(items),
            "average_score": round(sum(values) / len(values), 1) if values else 0,
            "graduation_ready": bool(profile and profile["graduation_ready"]),
        })

    return {
        "class_id": class_id,
        "class_name": class_obj.name,
        "student_count": len(students),
        "training_count": len(scores),
        "completed_students": sum(1 for item in student_rows if item["training_count"] > 0),
        "average_score": round(sum(percentages) / len(percentages), 1) if percentages else 0,
        "graduation_ready_count": sum(1 for profile in profiles if profile["graduation_ready"]),
        "score_distribution": score_distribution,
        "ability_distribution": ability_distribution,
        "common_weak_abilities": [
            {"name": name, "student_count": count}
            for name, count in weak_counter.most_common(3)
        ],
        "students": student_rows,
    }


@router.get("/{student_id}/comprehensive")
async def get_student_comprehensive(
    student_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_student_access(current_user, student_id, db)
    student = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    class_obj = (await db.execute(select(Class).where(Class.id == student.class_id))).scalar_one_or_none()
    scores = await ScoreService(db).get_student_scores(student_id, page_size=100)
    ability = await AbilityService(db).get_student_profile(student_id)
    reports = list((await db.execute(
        select(DiagnosticReport)
        .where(DiagnosticReport.student_id == student_id)
        .order_by(DiagnosticReport.generated_at.desc())
        .limit(5)
    )).scalars().all())
    checks = list((await db.execute(
        select(EnvironmentCheck)
        .where(EnvironmentCheck.student_id == student_id)
        .order_by(EnvironmentCheck.checked_at.desc())
        .limit(5)
    )).scalars().all())
    return {
        "student": {
            "id": student.id,
            "student_no": student.student_no,
            "name": student.name,
            "class_name": class_obj.name if class_obj else None,
        },
        "score_summary": scores.model_dump(mode="json"),
        "ability": ability.model_dump(mode="json") if ability else None,
        "reports": [
            {"id": item.id, "title": item.title, "report_type": item.report_type.value, "generated_at": item.generated_at}
            for item in reports
        ],
        "environment_checks": [
            {"id": item.id, "total_score": item.total_score, "summary": item.summary, "checked_at": item.checked_at}
            for item in checks
        ],
    }


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取学生详情"""
    await require_student_access(current_user, student_id, db)
    
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # Get major and class names
    major_result = await db.execute(
        select(Major).where(Major.id == student.major_id)
    )
    major = major_result.scalar_one_or_none()
    
    class_result = await db.execute(
        select(Class).where(Class.id == student.class_id)
    )
    cls = class_result.scalar_one_or_none()
    
    return StudentResponse(
        id=student.id,
        student_no=student.student_no,
        name=student.name,
        major_id=student.major_id,
        major_name=major.name if major else None,
        class_id=student.class_id,
        class_name=cls.name if cls else None,
        enrollment_year=student.enrollment_year,
    )
