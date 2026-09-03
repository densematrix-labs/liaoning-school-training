"""Role-specific data-scope tests."""

import pytest
from passlib.context import CryptContext

from app.models.student import Class, Major
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
