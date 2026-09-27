"""End-to-end unit/integration coverage for the tender acceptance workflows."""

from datetime import datetime, timedelta
import json
import stat

import pytest

from app.models.ability import MajorAbility, SubAbility
from app.models.lab import EnvironmentCheck, Lab
from app.models.report import DiagnosticReport, ReportType
from app.models.student import Class, Major, Student
from app.models.training import Score, TrainingProject, TrainingRecord
from app.models.user import User, UserRole
from app.services.auth import AuthService
from app.services.environment import EnvironmentCheckService, process_environment_task
from app.services.report import ReportService, ensure_report_structure, process_report_task
from app.models.workflow import EnvironmentTask, ReportTask, TaskStatus
from sqlalchemy import select, text


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
async def test_admin_cleanup_exact_legacy_report_titles_is_backed_up_and_recoverable(
    client, test_db, auth_headers, acceptance_data, tmp_path, monkeypatch
):
    from app.config import settings

    ids = acceptance_data
    monkeypatch.setattr(settings, "REPORT_BACKUP_DIR", str(tmp_path / "private-backups"))
    async with test_db() as db:
        for report_id, title, generated_at in [
            ("legacy-report-1", "单次实训诊断", "2024-01-01 00:00:00"),
            ("legacy-report-2", "单次实训诊断报告", "2024-01-02 00:00:00"),
        ]:
            await db.execute(text(
                "INSERT INTO diagnostic_reports "
                "(id, student_id, report_type, title, content, score_id, generated_at) "
                "VALUES (:id, :student_id, 'SINGLE', :title, :content, :score_id, :generated_at)"
            ), {
                "id": report_id,
                "student_id": ids["student"],
                "title": title,
                "content": f"{title}完整正文",
                "score_id": ids["score"],
                "generated_at": generated_at,
            })
        db.add(ReportTask(
            id="legacy-report-task",
            student_id=ids["student"],
            score_id=ids["score"],
            report_type="single",
            report_id="legacy-report-1",
            status=TaskStatus.COMPLETED,
            created_by=ids["teacher"],
        ))
        await db.commit()

    preview = await client.get("/api/v1/admin/maintenance/legacy-report-cleanup", headers=auth_headers)
    assert preview.status_code == 200
    assert preview.json()["matched_count"] == 2
    assert preview.json()["delete_count"] == 2
    assert preview.json()["preserved_count"] == 0
    assert {row["title"] for row in preview.json()["records"]} == {"单次实训诊断", "单次实训诊断报告"}
    assert preview.json()["latest_new_format"]["title"] == "验收报告"

    denied = await client.post(
        "/api/v1/admin/maintenance/legacy-report-cleanup",
        headers=auth_headers,
        json={"confirm": "wrong"},
    )
    assert denied.status_code == 400
    cleaned = await client.post(
        "/api/v1/admin/maintenance/legacy-report-cleanup",
        headers=auth_headers,
        json={"confirm": "BACKUP_AND_DELETE_EXACT_LEGACY_REPORTS"},
    )
    assert cleaned.status_code == 200
    result = cleaned.json()
    assert result["deleted_count"] == 2
    assert result["remaining_legacy_count"] == 0
    assert result["new_format_count"] == 1
    assert result["backup"]["record_count"] == 2

    backup = tmp_path / "private-backups" / result["backup"]["filename"]
    assert backup.is_file()
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    payload = json.loads(backup.read_text(encoding="utf-8"))
    assert payload["format"].endswith("diagnostic-report-backup-v1")
    assert {row["id"] for row in payload["reports"]} == {"legacy-report-1", "legacy-report-2"}
    assert payload["linked_report_tasks"] == [
        {"task_id": "legacy-report-task", "report_id": "legacy-report-1"}
    ]
    async with test_db() as db:
        assert not list((await db.execute(
            select(DiagnosticReport).where(DiagnosticReport.id.in_(["legacy-report-1", "legacy-report-2"]))
        )).scalars())
        assert (await db.get(DiagnosticReport, ids["report"])).title == "验收报告"
        assert (await db.get(ReportTask, "legacy-report-task")).report_id is None


@pytest.mark.asyncio
async def test_cleanup_preserves_latest_report_when_it_still_has_legacy_title(
    client, test_db, auth_headers, acceptance_data, tmp_path, monkeypatch
):
    from app.config import settings

    ids = acceptance_data
    monkeypatch.setattr(settings, "REPORT_BACKUP_DIR", str(tmp_path / "private-backups"))
    async with test_db() as db:
        for report_id, generated_at in [
            ("legacy-older", "2098-01-01 00:00:00"),
            ("legacy-latest", "2099-01-01 00:00:00"),
        ]:
            await db.execute(text(
                "INSERT INTO diagnostic_reports "
                "(id, student_id, report_type, title, content, generated_at) "
                "VALUES (:id, :student_id, 'SINGLE', '单次实训诊断报告', '历史正文', :generated_at)"
            ), {"id": report_id, "student_id": ids["student"], "generated_at": generated_at})
        await db.commit()

    preview = (await client.get(
        "/api/v1/admin/maintenance/legacy-report-cleanup", headers=auth_headers
    )).json()
    assert preview["matched_count"] == 2
    assert preview["delete_count"] == 1
    assert preview["preserved_count"] == 1
    assert next(row for row in preview["records"] if row["preserved_as_latest"])["id"] == "legacy-latest"

    result = (await client.post(
        "/api/v1/admin/maintenance/legacy-report-cleanup",
        headers=auth_headers,
        json={"confirm": "BACKUP_AND_DELETE_EXACT_LEGACY_REPORTS"},
    )).json()
    assert result["deleted_count"] == 1
    assert result["remaining_legacy_count"] == 1
    async with test_db() as db:
        assert await db.get(DiagnosticReport, "legacy-latest")
        assert await db.get(DiagnosticReport, "legacy-older") is None


def test_future_reports_reject_exact_legacy_generic_titles():
    with pytest.raises(ValueError):
        DiagnosticReport(student_id="student", report_type=ReportType.SINGLE, title="单次实训诊断报告")
    allowed = DiagnosticReport(
        student_id="student",
        report_type=ReportType.SINGLE,
        title="机车启动与制动操作 · 2026-09-17 08:00 · 张伟诊断报告",
    )
    assert allowed.title.startswith("机车启动与制动操作")


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
    score_detail = (await client.get(f"/api/v1/scores/{ids['score']}", headers=student)).json()
    assert score_detail["record_reference"].startswith("TR-")
    assert "ACCEPT-EXT-001" not in score_detail["record_reference"]
    assert score_detail["project_name"] == "验收实训项目"
    assert score_detail["source_completed_at"]

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
    class_overview = (await client.get(f"/api/v1/students/classes/{ids['class']}/overview", headers=teacher)).json()
    assert class_overview["graduation_ready_count"] == 0
    assert class_overview["graduation_not_ready_count"] == 1
    assert class_overview["graduation_ready_rate"] == 0
    assert class_overview["students"][0]["graduation_progress"] == 0
    assert class_overview["students"][0]["graduation_ready_count"] == 0
    assert class_overview["ability_distribution"][0]["ready_count"] == 0
    comprehensive = (await client.get(f"/api/v1/students/{ids['student']}/comprehensive", headers=teacher)).json()
    assert comprehensive["ability"]["graduation_progress"] == 0
    assert comprehensive["ability"]["graduation_ready_count"] == 0
    report_list = await client.get(f"/api/v1/reports/student/{ids['student']}", headers=teacher)
    assert report_list.json()[0]["score_id"] == ids["score"]
    filtered_report_list = await client.get(
        f"/api/v1/reports/student/{ids['student']}",
        headers=teacher,
        params={"report_type": "single", "score_id": ids["score"]},
    )
    assert [item["id"] for item in filtered_report_list.json()] == [ids["report"]]
    assert (await client.get(
        f"/api/v1/reports/student/{ids['student']}",
        headers=teacher,
        params={"report_type": "periodic", "score_id": ids["score"]},
    )).json() == []
    assert (await client.get(
        f"/api/v1/reports/student/{ids['student']}",
        headers=teacher,
        params={"report_type": "unsupported"},
    )).status_code == 400

    for path in ["/api/v1/dashboard/", "/api/v1/dashboard/overview", "/api/v1/dashboard/realtime", "/api/v1/dashboard/ability-distribution", "/api/v1/dashboard/training-trend", "/api/v1/dashboard/class-comparison", "/api/v1/dashboard/alerts"]:
        response = await client.get(path, headers=auth_headers)
        assert response.status_code == 200, (path, response.text)
    dashboard = (await client.get("/api/v1/dashboard/", headers=auth_headers)).json()
    assert dashboard["graduation_summary"]["total_students"] == 1
    assert dashboard["graduation_summary"]["ready_count"] == 0
    assert dashboard["ability_distribution"][0]["threshold"] == 60
    assert dashboard["ability_distribution"][0]["ready_count"] == 0
    assert dashboard["score_distribution"] == [
        {"label": "<60", "count": 1},
        {"label": "60-69", "count": 0},
        {"label": "70-79", "count": 0},
        {"label": "80-89", "count": 0},
        {"label": "90-100", "count": 0},
    ]


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
        "/api/v1/admin/operations/performance-report",
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
    csv_content = "source_record_id,student_no,project_name,completed_at\nCSV-IMPORT-001,ACCEPT001,验收实训项目,2026-09-01T08:00:00\n".encode()
    preview = await client.post("/api/v1/admin/operations/sync-import/preview", headers=auth_headers, files={"file": ("records.csv", csv_content, "text/csv")})
    assert preview.status_code == 200
    assert preview.json()["valid_count"] == 1
    assert preview.json()["error_count"] == 0
    assert preview.json()["can_import"] is True
    template = await client.get("/api/v1/admin/operations/sync-import/template.csv", headers=auth_headers)
    assert template.status_code == 200
    assert b"source_record_id" in template.content
    imported = await client.post("/api/v1/admin/operations/sync-import", headers=auth_headers, files={"file": ("records.csv", csv_content, "text/csv")})
    assert imported.status_code == 200
    assert imported.json()["message"] == "导入数据成功"
    assert imported.json()["row_count"] == 1
    assert (await client.get("/api/v1/admin/sync/history", headers=auth_headers)).json() == []
    executed = await client.post("/api/v1/admin/sync", headers=auth_headers)
    assert executed.status_code == 200
    assert executed.json()["success_count"] == 1

    config = await client.put(f"/api/v1/admin/projects/{ids['project']}/configuration", headers=auth_headers, json={"steps": [{"id": "step-1", "name": "检查", "score": 30, "failed_score": 0}, {"id": "step-2", "name": "操作", "score": 70, "failed_score": 10}], "ability_mapping": {"step-1": [ids["sub"]], "step-2": [ids["sub"]]}})
    assert config.status_code == 200
    project_options = (await client.get("/api/v1/admin/projects", headers=auth_headers)).json()
    sample = next(item for item in project_options if item["id"] == ids["project"])["sample_scores"][0]
    assert sample["student_name"] == "验收学生"
    assert sample["student_no"] == "ACCEPT001"
    assert sample["class_name"] == "验收班"
    assert sample["project_name"] == "验收实训项目"
    assert sample["completed_at"]
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
    teacher = await _login(client, "ACCEPT-T")
    wrong_type = await client.post("/api/v1/admin/operations/sync-import", headers=auth_headers, files={"file": ("bad.txt", b"x", "text/plain")})
    assert wrong_type.status_code == 400
    empty = await client.post("/api/v1/admin/operations/sync-import", headers=auth_headers, files={"file": ("empty.csv", b"source_record_id\n", "text/csv")})
    assert empty.status_code == 400
    invalid_encoding = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("invalid-encoding.csv", b"\xff\xfe", "text/csv")},
    )
    assert invalid_encoding.status_code == 400
    too_many_rows = (
        "source_record_id,student_index,project_index,completed_at\n"
        + "".join(f"ROW-{index},0,0,2026-09-17T08:00:00\n" for index in range(5001))
    ).encode()
    assert (await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("too-many.csv", too_many_rows, "text/csv")},
    )).status_code == 400
    missing_fields = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("missing.csv", b"source_record_id,completed_at\nX,2026-09-17T08:00:00\n", "text/csv")},
    )
    assert missing_fields.status_code == 400
    missing_required_fields = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("missing-required.csv", b"student_index,project_index\n0,0\n", "text/csv")},
    )
    assert missing_required_fields.status_code == 400
    missing_student_column = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("missing-student.csv", b"source_record_id,project_index,completed_at\nX,0,2026-09-17T08:00:00\n", "text/csv")},
    )
    assert missing_student_column.status_code == 400
    missing_project_column = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("missing-project.csv", b"source_record_id,student_index,completed_at\nX,0,2026-09-17T08:00:00\n", "text/csv")},
    )
    assert missing_project_column.status_code == 400
    invalid_mapping = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("invalid.csv", "source_record_id,student_no,project_name,completed_at\nX,NO-STUDENT,不存在项目,bad-time\n".encode(), "text/csv")},
    )
    assert invalid_mapping.status_code == 200
    assert invalid_mapping.json()["can_import"] is False
    assert invalid_mapping.json()["error_count"] == 1
    invalid_indices = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("invalid-indices.csv", b"source_record_id,student_index,project_index,completed_at\n,not-a-number,also-bad,2026-09-17T08:00:00\n", "text/csv")},
    )
    assert invalid_indices.status_code == 200
    assert "缺少实训记录编号" in invalid_indices.json()["errors"][0]["reason"]
    assert "student_index 必须是整数" in invalid_indices.json()["errors"][0]["reason"]
    assert "project_index 必须是整数" in invalid_indices.json()["errors"][0]["reason"]
    missing_row_mapping = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("missing-row-mapping.csv", b"source_record_id,student_no,project_name,completed_at\nX,,,2026-09-17T08:00:00\n", "text/csv")},
    )
    assert missing_row_mapping.status_code == 200
    assert "缺少学号或学生索引" in missing_row_mapping.json()["errors"][0]["reason"]
    assert "缺少项目编码或项目索引" in missing_row_mapping.json()["errors"][0]["reason"]
    invalid_code = await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=auth_headers,
        files={"file": ("invalid-code.csv", b"source_record_id,student_index,project_code,completed_at\nX,0,NO-PROJECT,2026-09-17T08:00:00\n", "text/csv")},
    )
    assert invalid_code.status_code == 200
    assert "项目编码不存在" in invalid_code.json()["errors"][0]["reason"]
    rejected_import = await client.post(
        "/api/v1/admin/operations/sync-import",
        headers=auth_headers,
        files={"file": ("invalid.csv", "source_record_id,student_no,project_name,completed_at\nX,NO-STUDENT,不存在项目,bad-time\n".encode(), "text/csv")},
    )
    assert rejected_import.status_code == 400
    assert (await client.post(
        "/api/v1/admin/operations/sync-import",
        headers=teacher,
        files={"file": ("records.csv", b"source_record_id,student_index,project_index,completed_at\nX,0,0,2026-09-17T08:00:00\n", "text/csv")},
    )).status_code == 403
    assert (await client.post(
        "/api/v1/admin/operations/sync-import/preview",
        headers=teacher,
        files={"file": ("records.csv", b"source_record_id,student_index,project_index,completed_at\nX,0,0,2026-09-17T08:00:00\n", "text/csv")},
    )).status_code == 403
    assert (await client.get("/api/v1/admin/operations/sync-import/template.csv", headers=student)).status_code == 403
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
    last_json = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        type(self).last_json = kwargs.get("json")
        return _FakeResponse(self.content)


def test_legacy_report_text_is_wrapped_in_the_stable_section_template():
    structured = ensure_report_structure(
        "# 旧版诊断结论\n需要加强规范操作",
        report_type="single",
        project_name="历史实训项目",
        completed_at=None,
        score_total=None,
        score_max=None,
    )
    assert "## 整体评价" in structured
    assert "**旧版诊断结论**" in structured
    assert "## 能力分析" in structured
    assert "## 问题与薄弱环节" in structured
    assert "## 提升建议" in structured
    assert "## 关联实训" in structured
    assert "时间待确认" in structured
    assert "成绩待确认" in structured


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

    _FakeAsyncClient.content = "## 基本信息与成绩概况\n匿名学员：验收项目 50 分\n模型来源 bailian\n## 能力分析\nstep-2 与 accept-sub 需加强，sa-999 待复核，d9537c70 不应显示\n## 环境规范情况\n总体规范\n## 提升建议\n继续训练"
    monkeypatch.setattr(report_module.httpx, "AsyncClient", _FakeAsyncClient)
    async with test_db() as db:
        service = ReportService(db)
        report = await service.generate_report(ids["student"], "single", ids["score"])
        assert "验收项目" in report.content
        assert "验收学生" in report.content
        assert "step-" not in report.content
        assert "sa-" not in report.content
        assert "accept-sub" not in report.content
        assert "d9537c70" not in report.content
        assert "模型来源" not in report.content
        assert "bailian" not in report.content.lower()
        assert "## 问题与薄弱环节" in report.content
        assert "## 关联实训" in report.content
        prompt = _FakeAsyncClient.last_json["messages"][0]["content"]
        assert "验收学生" not in prompt
        assert ids["student"] not in prompt
        assert "匿名学员" in prompt
        assert "step-1" not in prompt
        assert "accept-sub" not in prompt
        with pytest.raises(ValueError):
            await service.generate_report(ids["student"], "invalid", ids["score"])
        assert await service.get_report("missing") is None
        assert await service.get_task("missing") is None

        db.add_all([
            DiagnosticReport(
                id="historic-single-without-score",
                student_id=ids["student"],
                report_type=ReportType.SINGLE,
                content="# 旧版单次报告\n模型来源 bailian\nstep-legacy 与 sa-legacy",
            ),
            DiagnosticReport(
                id="historic-periodic-without-score",
                student_id=ids["student"],
                report_type=ReportType.PERIODIC,
                content="# 旧版阶段报告\n学员-legacy 需要继续训练",
            ),
        ])
        await db.commit()
        historic_single = await service.get_report("historic-single-without-score")
        historic_periodic = await service.get_report("historic-periodic-without-score")
        assert historic_single.title.startswith("验收实训项目")
        assert historic_single.score_id == ids["score"]
        assert historic_single.project_name == "验收实训项目"
        assert "模型来源" not in historic_single.content
        assert "step-" not in historic_single.content
        assert "## 整体评价" in historic_single.content
        assert "## 能力分析" in historic_single.content
        assert "## 问题与薄弱环节" in historic_single.content
        assert "## 提升建议" in historic_single.content
        assert "## 关联实训" in historic_single.content
        assert historic_periodic.title.startswith("验收学生 · 阶段综合诊断报告")
        assert "验收学生" in historic_periodic.content
        filtered_historic = await service.get_student_reports(
            ids["student"], report_type="single", score_id=ids["score"], limit=20
        )
        assert "historic-single-without-score" in {item.id for item in filtered_historic}


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
    task_result = await client.get(f"/api/v1/reports/tasks/{report_task_id}", headers=teacher)
    assert task_result.status_code == 200
    assert task_result.json()["status"] == "completed"
    assert task_result.json()["report_id"]
    persisted_reports = await client.get(
        f"/api/v1/reports/student/{ids['student']}",
        headers=teacher,
        params={"report_type": "single", "score_id": ids["score"]},
    )
    assert any(item["id"] == task_result.json()["report_id"] for item in persisted_reports.json())
    assert (await client.get("/api/v1/reports/tasks/missing", headers=teacher)).status_code == 404
