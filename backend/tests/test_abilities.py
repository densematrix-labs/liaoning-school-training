import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ability import MajorAbility, SubAbility
from app.models.ability import AbilityProfile
from app.models.student import Class, Major, Student
from app.models.training import Score, TrainingProject
from app.models.user import User, UserRole
from app.services.ability import AbilityService


@pytest.mark.asyncio
async def test_get_ability_schema_empty(client: AsyncClient):
    """Test get ability schema when empty"""
    response = await client.get("/api/v1/abilities/schema")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_ability_schema(client: AsyncClient, db_session: AsyncSession):
    """Test get ability schema with data"""
    # Create test ability
    ma = MajorAbility(
        id="test-ma-001",
        name="测试能力",
        description="测试描述",
        weight=0.25,
        graduation_threshold=0.6,
        display_order=0,
    )
    db_session.add(ma)
    
    sa = SubAbility(
        id="test-sa-001",
        major_ability_id="test-ma-001",
        name="测试子能力",
        description="测试子能力描述",
        weight=0.5,
    )
    db_session.add(sa)
    await db_session.commit()
    
    response = await client.get("/api/v1/abilities/schema")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "测试能力"
    assert len(data[0]["sub_abilities"]) == 1


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """Test get profile without auth"""
    response = await client.get("/api/v1/abilities/profile")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_rebuilds_from_step_scores_not_seeded_values(db_session: AsyncSession):
    db_session.add(User(
        id="ability-user",
        username="ability-user",
        password_hash="unused",
        name="能力测试学生",
        role=UserRole.STUDENT,
    ))
    db_session.add(Major(id="ability-major", code="ABILITY", name="测试专业"))
    db_session.add(Class(
        id="ability-class",
        name="能力测试班",
        major_id="ability-major",
        year=2023,
    ))
    db_session.add(Student(
        id="ability-student",
        user_id="ability-user",
        student_no="ABILITY001",
        name="能力测试学生",
        major_id="ability-major",
        class_id="ability-class",
        enrollment_year=2023,
    ))
    db_session.add(MajorAbility(
        id="ability-major-safety",
        name="安全操作能力",
        weight=1,
        graduation_threshold=0.6,
        display_order=0,
    ))
    db_session.add(SubAbility(
        id="ability-sub-check",
        major_ability_id="ability-major-safety",
        name="作业前检查",
        weight=1,
    ))
    db_session.add(TrainingProject(
        id="ability-project",
        name="演示实训项目",
        major_id="ability-major",
        max_score=100,
    ))
    db_session.add(Score(
        id="ability-score",
        student_id="ability-student",
        project_id="ability-project",
        total_score=50,
        max_score=100,
        details={
            "step-1": {
                "score": 5,
                "max_score": 10,
                "related_abilities": ["ability-sub-check"],
            }
        },
    ))
    db_session.add(AbilityProfile(
        id="stale-profile",
        student_id="ability-student",
        major_abilities={"ability-major-safety": 0.99},
        sub_abilities={"ability-sub-check": 0.99},
        graduation_ready=True,
    ))
    await db_session.commit()

    result = await AbilityService(db_session).get_student_profile("ability-student")

    assert result is not None
    assert result.sub_abilities["ability-sub-check"] == 50
    assert result.major_abilities["ability-major-safety"] == 50
    assert result.total_score == 50
    assert result.graduation_ready is False
