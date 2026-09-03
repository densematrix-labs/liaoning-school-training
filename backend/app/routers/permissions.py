"""Role and data-scope permission helpers."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Class, Student
from app.schemas.auth import UserResponse


async def require_class_access(
    user: UserResponse,
    class_id: str,
    db: AsyncSession,
) -> None:
    if user.role == "admin":
        return
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")

    result = await db.execute(
        select(Class.id).where(Class.id == class_id, Class.teacher_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="无权访问该班级")


async def require_student_access(
    user: UserResponse,
    student_id: str,
    db: AsyncSession,
) -> None:
    if user.role == "admin":
        return
    if user.role == "student":
        if user.student_id != student_id:
            raise HTTPException(status_code=403, detail="无权访问该学生")
        return
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")

    result = await db.execute(
        select(Student.id)
        .join(Class, Student.class_id == Class.id)
        .where(Student.id == student_id, Class.teacher_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="无权访问该学生")
