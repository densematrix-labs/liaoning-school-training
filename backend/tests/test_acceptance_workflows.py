"""End-to-end unit/integration coverage for the tender acceptance workflows."""

from datetime import datetime, timedelta

import pytest

from app.models.ability import MajorAbility, SubAbility
from app.models.lab import EnvironmentCheck, Lab
from app.models.report import DiagnosticReport, ReportType
from app.models.student import Class, Major, Student
from app.models.training import Score, TrainingProject, TrainingRecord
from app.models.user import User, UserRole
from app.services.auth import AuthService
from app.services.environment import EnvironmentCheckService, process_environment_task
from app.services.report import ReportService, process_report_task
from app.models.workflow import EnvironmentTask, ReportTask, TaskStatus
from sqlalchemy import select


@pytest.fixture
def domain_ids():
    return {
        "major": "accept-major",
        "class": "accept-class",
        "teacher": "accept-teacher",
        "student_user": "accept-student-user",
        "student": "accept-student",
        "ability": "accept-ability",
        "sub": "accept-sub",
        "lab": "accept-lab",
        "project": "accept-project",
        "record": "accept-record",
        "score": "accept-score",
        "check": "accept-check",
        "report": "accept-report",
    }


@pytest.fixture
async def acceptance_data(test_db, domain_ids):
    ids = domain_ids
    hashed = AuthService.get_password_hash("123456")
    async with test_db() as db:
        db.add_all([
            User(id=ids["teacher"], username="ACCEPT-T", password_hash=hashed, name="验收教师", role=UserRole.TEACHER),
            User(id=ids["student_user"], username="ACCEPT-S", password_hash=hashed, name="验收学生", role=UserRole.STUDENT),
            Major(id=ids["major"], code="ACCEPT", name="验收专业"),
            Class(id=ids["class"], name="验收班", major_id=ids["major"], teacher_id=ids["teacher"], year=2024),
            Student(id=ids["student"], user_id=ids["student_user"], student_no="ACCEPT001", name="验收学生", major_id=ids["major"], class_id=ids["class"], enrollment_year=2024),
            MajorAbility(id=ids["ability"], name="规范操作", description="验收能力", weight=1, graduation_threshold=.6, display_order=1),
            SubAbility(id=ids["sub"], major_ability_id=ids["ability"], name="步骤执行", weight=1),
            Lab(id=ids["lab"], name="验收实训室", building="A", floor=1, capacity=40, equipment=["控制台"], reference_image_url="/reference.jpg"),
            TrainingProject(
                id=ids["project"], name="验收实训项目", major_id=ids["major"], lab_id=ids["lab"], duration=60, max_score=100,
                steps=[{"id": "step-1", "name": "检查", "score": 40, "failed_score": 0}, {"id": "step-2", "name": "操作", "score": 60, "failed_score": 10}],
                scoring_rules={"version": 1, "code": "P-001", "enabled": True, "repeat_policy": "keep_all"},
                ability_mapping={"step-1": [ids["sub"]], "step-2": [ids["sub"]]},
            ),
            TrainingRecord(id=ids["record"], external_id="ACCEPT-EXT-001", student_id=ids["student"], project_id=ids["project"], steps_data={"step-1": {"passed": True}, "step-2": {"passed": False, "reason": "顺序错误"}}, completed_at=datetime.utcnow() - timedelta(days=1)),
            Score(id=ids["score"], student_id=ids["student"], project_id=ids["project"], record_id=ids["record"], total_score=50, max_score=100, details={"step-1": {"passed": True, "score": 40, "max_score": 40, "related_abilities": [ids["sub"]]}, "step-2": {"passed": False, "score": 10, "max_score": 60, "reason": "顺序错误", "related_abilities": [ids["sub"]]}}, failed_abilities=[ids["sub"]], calculated_at=datetime.utcnow() - timedelta(days=1)),
            EnvironmentCheck(id=ids["check"], student_id=ids["student"], lab_id=ids["lab"], score_id=ids["score"], uploaded_image_url="data:image/png;base64,AA==", total_score=80, details={"surface_cleanliness": {"score": 20, "max_score": 30, "issues": ["遗留物"]}, "__suggestions__": ["清理台面"]}, summary="需要整理"),
            DiagnosticReport(id=ids["report"], student_id=ids["student"], report_type=ReportType.SINGLE, title="验收报告", content="# 诊断\n需要加强步骤执行", score_id=ids["score"]),
        ])
        await db.commit()
    return ids


async def _login(client, username):
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": "123456"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_student_teacher_and_dashboard_acceptance(client, auth_headers, acceptance_data):
    ids = acceptance_data
    teacher = await _login(client, "ACCEPT-T")
    student = await _login(client, "ACCEPT-S")
    form_login = await client.post("/api/v1/auth/login/form", data={"username": "ACCEPT-S", "password": "123456"})
    assert form_login.status_code == 200
    refreshed = await client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {form_login.json()['access_token']}"})
    assert refreshed.status_code == 200

    student_paths = [
        "/api/v1/students/me",
        "/api/v1/students/me/training-records",
        f"/api/v1/students/me/training-records/{ids['record']}",
        "/api/v1/students/me/ability-map",
        "/api/v1/students/me/reports",
        f"/api/v1/students/me/reports/{ids['report']}",
        "/api/v1/students/me/graduation-progress",
        "/api/v1/scores/",
        f"/api/v1/scores/{ids['score']}",
        "/api/v1/abilities/profile",
        f"/api/v1/abilities/student/{ids['student']}/trend",
        f"/api/v1/environment/history/{ids['student']}",
        "/api/v1/reports/",
        f"/api/v1/reports/{ids['report']}",
        f"/api/v1/reports/{ids['report']}/download.doc",
    ]
    for path in student_paths:
        response = await client.get(path, headers=student)
        assert response.status_code == 200, (path, response.text)

    teacher_paths = [
        "/api/v1/students/classes",
        f"/api/v1/students/classes/{ids['class']}",
        f"/api/v1/students/classes/{ids['class']}/students",
        f"/api/v1/students/classes/{ids['class']}/overview",
        f"/api/v1/students/{ids['student']}/comprehensive",
        f"/api/v1/students/{ids['student']}",
        f"/api/v1/scores/student/{ids['student']}",
        f"/api/v1/scores/class/{ids['class']}",
        f"/api/v1/scores/class/{ids['class']}/summary",
        f"/api/v1/scores/class/{ids['class']}/export.csv",
        f"/api/v1/abilities/student/{ids['student']}",
        f"/api/v1/abilities/class/{ids['class']}",
        f"/api/v1/reports/student/{ids['student']}",
    ]
    for path in teacher_paths:
        response = await client.get(path, headers=teacher)
        assert response.status_code == 200, (path, response.text)

    for path in ["/api/v1/dashboard/", "/api/v1/dashboard/overview", "/api/v1/dashboard/realtime", "/api/v1/dashboard/ability-distribution", "/api/v1/dashboard/training-trend", "/api/v1/dashboard/class-comparison", "/api/v1/dashboard/alerts"]:
        response = await client.get(path, headers=auth_headers)
        assert response.status_code == 200, (path, response.text)


@pytest.mark.asyncio
async def test_admin_configuration_and_operations(client, auth_headers, acceptance_data):
    ids = acceptance_data
    reads = [
        "/api/v1/admin/overview",
        "/api/v1/admin/access-control",
        "/api/v1/admin/abilities",
        "/api/v1/admin/labs",
        "/api/v1/admin/projects",
        "/api/v1/admin/mappings",
        "/api/v1/admin/operations/status",
        "/api/v1/admin/operations/sync-schedule",
        "/api/v1/admin/operations/accounts",
        "/api/v1/admin/operations/classes",
        "/api/v1/admin/operations/projects",
        "/api/v1/admin/operations/backups",
        "/api/v1/admin/operations/audit-logs",
        f"/api/v1/admin/operations/labs/{ids['lab']}/reference-images",
    ]
    for path in reads:
        response = await client.get(path, headers=auth_headers)
        assert response.status_code == 200, (path, response.text)

    schedule = await client.put("/api/v1/admin/operations/sync-schedule", headers=auth_headers, json={"enabled": True, "frequency_hours": 12, "hour": 3})
    assert schedule.json()["frequency_hours"] == 12

    account = await client.post("/api/v1/admin/operations/accounts", headers=auth_headers, json={"username": "NEW-TEACHER", "name": "新教师", "role": "teacher", "password": "123456"})
    assert account.status_code == 200
    duplicate = await client.post("/api/v1/admin/operations/accounts", headers=auth_headers, json={"username": "NEW-TEACHER", "name": "新教师", "role": "teacher", "password": "123456"})
    assert duplicate.status_code == 409

    class_response = await client.post("/api/v1/admin/operations/classes", headers=auth_headers, json={"name": "新增班", "major_id": ids["major"], "year": 2025, "teacher_id": ids["teacher"]})
    assert class_response.status_code == 200
    project_response = await client.post("/api/v1/admin/operations/projects", headers=auth_headers, json={"name": "新增项目", "code": "NEW-P", "major_id": ids["major"], "lab_id": ids["lab"], "duration": 45, "max_score": 100})
    assert project_response.status_code == 200
    image_response = await client.post(f"/api/v1/admin/operations/labs/{ids['lab']}/reference-images", headers=auth_headers, json={"image_url": "/reference-2.jpg", "label": "侧视图"})
    assert image_response.status_code == 200
    csv_content = b"source_record_id,student_index,project_index,completed_at\nCSV-IMPORT-001,0,1,2026-09-01T08:00:00\n"
    imported = await client.post("/api/v1/admin/operations/sync-import", headers=auth_headers, files={"file": ("records.csv", csv_content, "text/csv")})
    assert imported.status_code == 200
    assert imported.json()["success_count"] == 1

    config = await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [{"id": "step-1", "name": "检查", "score": 30, "failed_score": 0}, {"id": "step-2", "name": "操作", "score": 70, "failed_score": 10}], "ability_mapping": {"step-1": [ids["sub"]], "step-2": [ids["sub"]]}})
    assert config.status_code == 200
    recalc = await client.post(f"/api/v1/admin/projects/{ids['project']}/recalculate", headers=auth_headers, json={"score_id": ids["score"]})
    assert recalc.status_code == 200

    ability = await client.post("/api/v1/admin/abilities", headers=auth_headers, json={"name": "新增大类", "description": "描述", "weight": .2, "graduation_threshold": .7, "icon": "shield", "display_order": 9})
    assert ability.status_code == 200
    ability_id = ability.json()["id"]
    updated_ability = await client.put(f"/api/v1/admin/abilities/{ability_id}", headers=auth_headers, json={"name": "更新大类", "description": "更新描述", "weight": .3, "graduation_threshold": .75, "icon": "gear", "display_order": 10})
    assert updated_ability.status_code == 200
    sub = await client.post(f"/api/v1/admin/abilities/{ability_id}/sub-abilities", headers=auth_headers, json={"name": "新增子能力", "description": "说明", "weight": .5})
    assert sub.status_code == 200
    sub_id = sub.json()["id"]
    assert (await client.put(f"/api/v1/admin/sub-abilities/{sub_id}", headers=auth_headers, json={"name": "更新子能力", "description": "更新说明", "weight": .8})).status_code == 200
    assert (await client.delete(f"/api/v1/admin/sub-abilities/{sub_id}", headers=auth_headers)).status_code == 200
    assert (await client.delete(f"/api/v1/admin/abilities/{ability_id}", headers=auth_headers)).status_code == 200

    lab = await client.post("/api/v1/admin/labs", headers=auth_headers, json={"name": "新增实训室", "building": "B", "floor": 2, "capacity": 30, "equipment": ["设备"], "reference_image_url": "/lab.jpg"})
    assert lab.status_code == 200
    lab_id = lab.json()["id"]
    updated_lab = await client.put(f"/api/v1/admin/labs/{lab_id}", headers=auth_headers, json={"name": "更新实训室", "building": "C", "floor": 3, "capacity": 32, "equipment": ["设备2"], "reference_image_url": "/lab-2.jpg"})
    assert updated_lab.status_code == 200
    assert (await client.delete(f"/api/v1/admin/labs/{lab_id}", headers=auth_headers)).status_code == 200
    assert (await client.put(f"/api/v1/admin/mappings/{ids['project']}", headers=auth_headers, json={"step-1": [ids["sub"]]})).status_code == 200


@pytest.mark.asyncio
async def test_backup_creation_and_restore_verification(client, auth_headers, acceptance_data, monkeypatch, tmp_path):
    import sqlite3
    from app.config import settings

    source = tmp_path / "training.db"
    connection = sqlite3.connect(source)
    try:
        for table in ("users", "students", "training_records", "scores"):
            connection.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY)")
            connection.execute(f"INSERT INTO {table} VALUES ('sample')")
        connection.commit()
    finally:
        connection.close()
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite+aiosqlite:///{source}")
    created = await client.post("/api/v1/admin/operations/backups", headers=auth_headers)
    assert created.status_code == 200
    backup_id = created.json()["id"]
    verified = await client.post(f"/api/v1/admin/operations/backups/{backup_id}/verify", headers=auth_headers)
    assert verified.status_code == 200
    assert verified.json()["verified"] is True
    assert verified.json()["checksum_matches"] is True


@pytest.mark.asyncio
async def test_import_validation_and_permission_failures(client, auth_headers, acceptance_data):
    ids = acceptance_data
    student = await _login(client, "ACCEPT-S")
    wrong_type = await client.post("/api/v1/admin/operations/sync-import", headers=auth_headers, files={"file": ("bad.txt", b"x", "text/plain")})
    assert wrong_type.status_code == 400
    empty = await client.post("/api/v1/admin/operations/sync-import", headers=auth_headers, files={"file": ("empty.csv", b"source_record_id\n", "text/csv")})
    assert empty.status_code == 400
    forbidden = await client.get("/api/v1/admin/operations/status", headers=student)
    assert forbidden.status_code == 403
    other_student = await client.get("/api/v1/students/not-owned", headers=student)
    assert other_student.status_code == 403
    missing_report = await client.get("/api/v1/reports/missing", headers=student)
    assert missing_report.status_code == 404
    assert (await client.put("/api/v1/admin/classes/missing/teacher", headers=auth_headers, json={"teacher_id": None})).status_code == 404
    assert (await client.put(f"/api/v1/admin/classes/{ids['class']}/teacher", headers=auth_headers, json={"teacher_id": ids["student_user"]})).status_code == 400
    assert (await client.put("/api/v1/admin/abilities/missing", headers=auth_headers, json={"name": "x"})).status_code == 404
    assert (await client.post("/api/v1/admin/abilities/missing/sub-abilities", headers=auth_headers, json={"name": "x"})).status_code == 404
    assert (await client.put("/api/v1/admin/sub-abilities/missing", headers=auth_headers, json={"name": "x"})).status_code == 404
    assert (await client.put("/api/v1/admin/labs/missing", headers=auth_headers, json={"name": "x"})).status_code == 404
    assert (await client.put("/api/v1/admin/projects/missing/configuration", headers=auth_headers, json={"steps": [{"id": "x", "score": 1}], "ability_mapping": {}})).status_code == 404
    assert (await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [], "ability_mapping": {}})).status_code == 400
    assert (await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [{"id": "x", "score": 1}, {"id": "x", "score": 1}], "ability_mapping": {}})).status_code == 400
    assert (await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [{"id": "x", "score": 0}], "ability_mapping": {}})).status_code == 400
    assert (await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [{"id": "x", "score": 1, "failed_score": 2}], "ability_mapping": {}})).status_code == 400
    assert (await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [{"id": "x", "score": 1}], "ability_mapping": {"missing": [ids['sub']]}})).status_code == 400
    assert (await client.post("/api/v1/admin/projects/missing/recalculate", headers=auth_headers, json={})).status_code == 400
    assert (await client.put("/api/v1/admin/mappings/missing", headers=auth_headers, json={})).status_code == 404

    assert (await client.post("/api/v1/environment/tasks", headers=student, json={"student_id": ids["student"], "lab_id": ids["lab"], "image_base64": "data:image/png;base64,AA=="})).status_code == 403
    assert (await client.get("/api/v1/environment/tasks/missing", headers=student)).status_code == 403
    assert (await client.post("/api/v1/environment/check", headers=student, json={"student_id": ids["student"], "lab_id": ids["lab"], "image_base64": "data:image/png;base64,AA=="})).status_code == 403
    assert (await client.get("/api/v1/environment/checks/missing", headers=student)).status_code == 404
    assert (await client.post(f"/api/v1/environment/checks/{ids['check']}/review", headers=student, json={"status": "confirmed"})).status_code == 403


class _FakeResponse:
    def __init__(self, content):
        self._content = content
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeAsyncClient:
    content = ""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        return _FakeResponse(self.content)


@pytest.mark.asyncio
async def test_real_model_workflows_are_structured_and_traceable(test_db, acceptance_data, monkeypatch):
    from app.config import settings
    import app.services.environment as environment_module
    import app.services.report as report_module

    ids = acceptance_data
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    env_json = '{"total_score":88,"categories":{"equipment_placement":{"score":28,"max_score":30,"issues":[]},"surface_cleanliness":{"score":25,"max_score":30,"issues":["少量遗留物"]},"safety_compliance":{"score":18,"max_score":20,"issues":[]},"environmental_hygiene":{"score":17,"max_score":20,"issues":[]}},"summary":"总体规范","suggestions":["清理台面"]}'
    _FakeAsyncClient.content = f"```json\n{env_json}\n```"
    monkeypatch.setattr(environment_module.httpx, "AsyncClient", _FakeAsyncClient)
    async with test_db() as db:
        service = EnvironmentCheckService(db)
        result = await service.check_environment(ids["student"], ids["lab"], "data:image/png;base64,AA==", ids["score"])
        assert result.total_score == 88
        assert result.summary == "总体规范"
        assert await service.get_check("missing") is None
        with pytest.raises(ValueError):
            await service.create_task(ids["student"], ids["lab"], "not-an-image", None, ids["teacher"])
        with pytest.raises(ValueError):
            await service.review_check("missing", ids["teacher"], type("Review", (), {"status": "confirmed", "reviewed_details": None, "reviewed_summary": None, "note": None})())

    _FakeAsyncClient.content = "## 基本信息与成绩概况\n验收项目 50 分\n## 能力分析\n步骤执行需加强\n## 环境规范情况\n总体规范\n## 提升建议\n继续训练"
    monkeypatch.setattr(report_module.httpx, "AsyncClient", _FakeAsyncClient)
    async with test_db() as db:
        service = ReportService(db)
        report = await service.generate_report(ids["student"], "single", ids["score"])
        assert "验收项目" in report.content
        with pytest.raises(ValueError):
            await service.generate_report(ids["student"], "invalid", ids["score"])
        assert await service.get_report("missing") is None
        assert await service.get_task("missing") is None


@pytest.mark.asyncio
async def test_background_tasks_record_success_and_failure(test_db, acceptance_data, monkeypatch):
    import app.services.environment as environment_module
    import app.services.report as report_module
    from app.config import settings

    ids = acceptance_data
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(environment_module, "AsyncSessionLocal", test_db)
    monkeypatch.setattr(report_module, "AsyncSessionLocal", test_db)
    env_json = '{"total_score":90,"categories":{"equipment_placement":{"score":30,"max_score":30,"issues":[]},"surface_cleanliness":{"score":25,"max_score":30,"issues":[]},"safety_compliance":{"score":20,"max_score":20,"issues":[]},"environmental_hygiene":{"score":15,"max_score":20,"issues":[]}},"summary":"通过","suggestions":[]}'
    _FakeAsyncClient.content = env_json
    monkeypatch.setattr(environment_module.httpx, "AsyncClient", _FakeAsyncClient)
    async with test_db() as db:
        env_task = EnvironmentTask(id="env-background", student_id=ids["student"], lab_id=ids["lab"], score_id=ids["score"], image_data="data:image/png;base64,AA==", status=TaskStatus.PENDING, created_by=ids["teacher"])
        db.add(env_task)
        await db.commit()
    await process_environment_task("env-background")
    async with test_db() as db:
        task = (await db.execute(select(EnvironmentTask).where(EnvironmentTask.id == "env-background"))).scalar_one()
        assert task.status == TaskStatus.COMPLETED
        assert task.check_id

    _FakeAsyncClient.content = "# 完整报告\n成绩概况、能力分析、薄弱环节、环境规范情况、改进建议"
    monkeypatch.setattr(report_module.httpx, "AsyncClient", _FakeAsyncClient)
    async with test_db() as db:
        report_task = ReportTask(id="report-background", student_id=ids["student"], score_id=ids["score"], report_type="single", status=TaskStatus.PENDING, created_by=ids["teacher"])
        db.add(report_task)
        await db.commit()
    await process_report_task("report-background")
    async with test_db() as db:
        task = (await db.execute(select(ReportTask).where(ReportTask.id == "report-background"))).scalar_one()
        assert task.status == TaskStatus.COMPLETED
        assert task.report_id

    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    async with test_db() as db:
        failed = ReportTask(id="report-failed", student_id=ids["student"], score_id=ids["score"], report_type="single", status=TaskStatus.PENDING, created_by=ids["teacher"])
        db.add(failed)
        await db.commit()
    await process_report_task("report-failed")
    async with test_db() as db:
        task = (await db.execute(select(ReportTask).where(ReportTask.id == "report-failed"))).scalar_one()
        assert task.status == TaskStatus.FAILED
        assert task.error_message


@pytest.mark.asyncio
async def test_environment_and_report_http_workflows(client, test_db, acceptance_data, monkeypatch):
    import app.services.environment as environment_module
    import app.services.report as report_module
    from app.config import settings

    ids = acceptance_data
    teacher = await _login(client, "ACCEPT-T")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(environment_module, "AsyncSessionLocal", test_db)
    monkeypatch.setattr(report_module, "AsyncSessionLocal", test_db)
    _FakeAsyncClient.content = '{"total_score":92,"categories":{"equipment_placement":{"score":30,"max_score":30,"issues":[]},"surface_cleanliness":{"score":27,"max_score":30,"issues":[]},"safety_compliance":{"score":20,"max_score":20,"issues":[]},"environmental_hygiene":{"score":15,"max_score":20,"issues":[]}},"summary":"现场规范","suggestions":[]}'
    monkeypatch.setattr(environment_module.httpx, "AsyncClient", _FakeAsyncClient)

    assert (await client.get("/api/v1/environment/labs")).status_code == 200
    assert (await client.get(f"/api/v1/environment/labs/{ids['lab']}")).status_code == 200
    assert (await client.get("/api/v1/environment/labs/missing")).status_code == 404
    direct = await client.post("/api/v1/environment/check", headers=teacher, json={"student_id": ids["student"], "lab_id": ids["lab"], "score_id": ids["score"], "image_base64": "data:image/png;base64,AA=="})
    assert direct.status_code == 200
    check_id = direct.json()["id"]
    assert (await client.get(f"/api/v1/environment/checks/{check_id}", headers=teacher)).status_code == 200
    reviewed = await client.post(f"/api/v1/environment/checks/{check_id}/review", headers=teacher, json={"status": "confirmed", "note": "现场确认"})
    assert reviewed.status_code == 200

    task_response = await client.post("/api/v1/environment/tasks", headers=teacher, json={"student_id": ids["student"], "lab_id": ids["lab"], "score_id": ids["score"], "image_base64": "data:image/png;base64,AA=="})
    assert task_response.status_code == 200
    task_id = task_response.json()["id"]
    assert (await client.get(f"/api/v1/environment/tasks/{task_id}", headers=teacher)).status_code == 200
    assert (await client.get("/api/v1/environment/tasks/missing", headers=teacher)).status_code == 404

    _FakeAsyncClient.content = "# HTTP 报告\n成绩概况、能力分析、薄弱环节、环境规范情况、改进建议"
    monkeypatch.setattr(report_module.httpx, "AsyncClient", _FakeAsyncClient)
    generated = await client.post("/api/v1/reports/generate", headers=teacher, json={"student_id": ids["student"], "report_type": "single", "score_id": ids["score"]})
    assert generated.status_code == 200
    report_task_id = generated.json()["id"]
    assert (await client.get(f"/api/v1/reports/tasks/{report_task_id}", headers=teacher)).status_code == 200
    assert (await client.get("/api/v1/reports/tasks/missing", headers=teacher)).status_code == 404
