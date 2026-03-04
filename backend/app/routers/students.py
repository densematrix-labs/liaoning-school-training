from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.student import Student, Class, Major
from app.schemas.auth import UserResponse
from app.schemas.student import StudentResponse, ClassResponse, MajorResponse

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
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
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
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
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


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取学生详情"""
    # Check permission
    if current_user.role == "student":
        if current_user.student_id != student_id:
            raise HTTPException(status_code=403, detail="无权访问")
    elif current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
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
