"""招标功能参数的证据链与审计闭环测试。"""

import pytest
from sqlalchemy import select

from app.models.ability import AbilityProfile, MajorAbility, SubAbility
from app.models.lab import EnvironmentCheck, Lab
from app.models.student import Class, Major, Student
from app.models.training import Score, TrainingProject, TrainingRecord
from app.models.user import User, UserRole
from app.models.workflow import EnvironmentReview
from app.services.recalculation import RecalculationService
from app.services.environment import EnvironmentCheckService
from app.services.report import ReportService


@pytest.mark.asyncio
async def test_rule_recalculation_updates_score_and_ability_evidence(db_session):
    db_session.add_all([
        User(id="workflow-student-user", username="workflow-student", password_hash="unused", name="测试学生", role=UserRole.STUDENT),
        Major(id="workflow-major", code="WF", name="测试专业"),
        Class(id="workflow-class", name="测试班", major_id="workflow-major", year=2023),
        Student(id="workflow-student", user_id="workflow-student-user", student_no="WF001", name="测试学生", major_id="workflow-major", class_id="workflow-class", enrollment_year=2023),
        MajorAbility(id="workflow-major-ability", name="规范操作", weight=1, graduation_threshold=.6),
        SubAbility(id="workflow-sub-ability", major_ability_id="workflow-major-ability", name="步骤执行", weight=1),
        TrainingProject(
            id="workflow-project",
            name="可追溯实训",
            major_id="workflow-major",
            max_score=20,
            steps=[
                {"id": "step-1", "name": "第一步", "score": 10, "failed_score": 0},
                {"id": "step-2", "name": "第二步", "score": 10, "failed_score": 2},
            ],
            scoring_rules={"mode": "passed_or_failed", "version": 3},
            ability_mapping={"step-1": ["workflow-sub-ability"], "step-2": ["workflow-sub-ability"]},
        ),
        TrainingRecord(
            id="workflow-record",
            external_id="MOCK-WF-001",
            student_id="workflow-student",
            project_id="workflow-project",
            steps_data={"step-1": {"passed": True}, "step-2": {"passed": False, "reason": "顺序错误"}},
        ),
        Score(id="workflow-score", student_id="workflow-student", project_id="workflow-project", record_id="workflow-record", total_score=99, max_score=100, details={}),
    ])
    await db_session.commit()

    result = await RecalculationService(db_session).recalculate_score("workflow-score")
    assert result["before_total"] == 99
    assert result["after_total"] == 12
    assert result["source_record_id"] == "MOCK-WF-001"
    assert result["details"]["step-2"]["applied_rule"] == {
        "passed_score": 10.0,
        "failed_score": 2.0,
        "rule_version": 3,
    }
    profile = (await db_session.execute(select(AbilityProfile).where(AbilityProfile.student_id == "workflow-student"))).scalar_one()
    assert profile.sub_abilities["workflow-sub-ability"] == pytest.approx(.6)
    report_task = await ReportService(db_session).create_task(
        "workflow-student", "single", "workflow-score", "workflow-student-user"
    )
    assert report_task.status == "pending"
    assert report_task.score_id == "workflow-score"


@pytest.mark.asyncio
async def test_mock_sync_is_repeatable_and_keeps_exception_audit(client, auth_headers):
    first = await client.post("/api/v1/admin/sync", headers=auth_headers)
    second = await client.post("/api/v1/admin/sync", headers=auth_headers)
    history = await client.get("/api/v1/admin/sync/history", headers=auth_headers)

    assert first.status_code == second.status_code == history.status_code == 200
    assert first.json()["success_count"] == 3
    assert second.json()["success_count"] == 0
    assert second.json()["skipped_count"] == 5
    assert second.json()["exceptions"][0]["source_record_id"] == "DEMO-INVALID-001"
    assert len(history.json()) == 2


@pytest.mark.asyncio
async def test_admin_can_assign_teacher_scope(client, auth_headers, test_db):
    async with test_db() as session:
        session.add(User(id="scope-teacher", username="scope-teacher", password_hash="unused", name="范围教师", role=UserRole.TEACHER))
        session.add(Major(id="scope-major", code="SCOPE", name="权限专业"))
        session.add(Class(id="scope-class", name="权限班", major_id="scope-major", year=2024))
        await session.commit()

    update = await client.put("/api/v1/admin/classes/scope-class/teacher", headers=auth_headers, json={"teacher_id": "scope-teacher"})
    overview = await client.get("/api/v1/admin/access-control", headers=auth_headers)
    assert update.status_code == overview.status_code == 200
    assigned = next(item for item in overview.json()["classes"] if item["id"] == "scope-class")
    assert assigned["teacher_id"] == "scope-teacher"
    assert assigned["teacher_name"] == "范围教师"


@pytest.mark.asyncio
async def test_environment_review_preserves_ai_result_and_reviewer(client, auth_headers, test_db):
    async with test_db() as session:
        session.add(User(id="env-student-user", username="env-student", password_hash="unused", name="环境学生", role=UserRole.STUDENT))
        session.add(Major(id="env-major", code="ENV", name="环境专业"))
        session.add(Class(id="env-class", name="环境班", major_id="env-major", year=2024))
        session.add(Student(id="env-student", user_id="env-student-user", student_no="ENV001", name="环境学生", major_id="env-major", class_id="env-class", enrollment_year=2024))
        session.add(Lab(id="env-lab", name="环境实训室", reference_image_url="https://example.com/reference.jpg"))
        session.add(EnvironmentCheck(
            id="env-check",
            student_id="env-student",
            lab_id="env-lab",
            uploaded_image_url="data:image/png;base64,AA==",
            total_score=80,
            details={"surface_cleanliness": {"score": 20, "max_score": 30, "issues": ["台面有遗留物"]}},
            summary="AI 原始结论",
        ))
        await session.commit()
        task = await EnvironmentCheckService(session).create_task(
            "env-student", "env-lab", "data:image/png;base64,AA==", None, "test-user-1"
        )
        assert task.status == "pending"

    response = await client.post(
        "/api/v1/environment/checks/env-check/review",
        headers=auth_headers,
        json={
            "status": "modified",
            "reviewed_details": {"surface_cleanliness": {"score": 25, "max_score": 30, "issues": []}},
            "reviewed_summary": "人工复核后调整",
            "note": "已核对现场",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "AI 原始结论"
    assert data["reviewed_summary"] == "人工复核后调整"
    assert data["reviewer_name"] == "Test User"
    async with test_db() as session:
        review = (await session.execute(select(EnvironmentReview).where(EnvironmentReview.check_id == "env-check"))).scalar_one()
        assert review.status == "modified"
