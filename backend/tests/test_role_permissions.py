"""Role-specific data-scope tests."""

import pytest
from passlib.context import CryptContext

from app.models.student import Class, Major, Student
from app.models.user import User, UserRole


async def login(client, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "testpass"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def role_records():
    password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("testpass")
    return {
        "users": [
            User(id="teacher-a", username="teacher-a", password_hash=password_hash, name="教师甲", role=UserRole.TEACHER),
            User(id="teacher-b", username="teacher-b", password_hash=password_hash, name="教师乙", role=UserRole.TEACHER),
            User(id="admin-a", username="admin-a", password_hash=password_hash, name="管理员", role=UserRole.ADMIN),
        ],
        "major": Major(id="major-a", code="500113", name="铁道机车运用与维护"),
        "classes": [
            Class(id="class-a", name="甲班", major_id="major-a", teacher_id="teacher-a", year=2023),
            Class(id="class-b", name="乙班", major_id="major-a", teacher_id="teacher-b", year=2023),
        ],
    }


@pytest.mark.asyncio
async def test_teacher_can_only_access_assigned_class(client, test_db, role_records):
    async with test_db() as session:
        session.add_all(role_records["users"])
        session.add(role_records["major"])
        session.add_all(role_records["classes"])
        await session.commit()

    headers = await login(client, "teacher-a")
    own = await client.get("/api/v1/students/classes/class-a/students", headers=headers)
    other = await client.get("/api/v1/students/classes/class-b/students", headers=headers)

    assert own.status_code == 200
    assert other.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_every_class(client, test_db, role_records):
    async with test_db() as session:
        session.add_all(role_records["users"])
        session.add(role_records["major"])
        session.add_all(role_records["classes"])
        await session.commit()

    headers = await login(client, "admin-a")
    response = await client.get("/api/v1/students/classes/class-b/students", headers=headers)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_run_environment_check(client, student_headers):
    response = await client.post(
        "/api/v1/environment/check",
        headers=student_headers,
        json={
            "student_id": "test-student",
            "lab_id": "test-lab",
            "image_base64": "not-used",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_access_other_class_ability_or_student_profile(client, test_db, role_records):
    password_hash = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("testpass")
    async with test_db() as session:
        session.add_all(role_records["users"])
        session.add(role_records["major"])
        session.add_all(role_records["classes"])
        session.add(User(id="student-b-user", username="student-b", password_hash=password_hash, name="乙班学生", role=UserRole.STUDENT))
        session.add(Student(id="student-b", user_id="student-b-user", student_no="B001", name="乙班学生", major_id="major-a", class_id="class-b", enrollment_year=2023))
        await session.commit()

    headers = await login(client, "teacher-a")
    class_ability = await client.get("/api/v1/abilities/class/class-b", headers=headers)
    student_ability = await client.get("/api/v1/abilities/student/student-b", headers=headers)
    student_scores = await client.get("/api/v1/scores/student/student-b", headers=headers)

    assert class_ability.status_code == 403
    assert student_ability.status_code == 403
    assert student_scores.status_code == 403
