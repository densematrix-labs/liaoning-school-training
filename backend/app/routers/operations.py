import hashlib
import csv
import io
import os
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.controllers.auth import get_current_admin
from app.config import settings
from app.database import get_db
from app.models.operations import AuditLog, BackupRecord, ReferenceImage, SystemSetting
from app.models.user import User, UserRole
from app.models.student import Class, Major, Student, TeacherClassAssignment
from app.models.training import TrainingProject
from app.models.workflow import MockSyncTask
from app.services.auth import AuthService
from app.services.audit import record_audit
from app.services.sync import PENDING_SYNC_SETTING_KEY

router = APIRouter(prefix="/api/v1/admin/operations", tags=["运行管理"])


class ScheduleUpdate(BaseModel):
    enabled: bool = True
    frequency_hours: int = Field(24, ge=1, le=168)
    hour: int = Field(2, ge=0, le=23)


class AccountCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    role: UserRole
    password: str = Field(default="123456", min_length=6, max_length=72)


class ClassCreate(BaseModel):
    name: str
    major_id: str
    year: int = Field(ge=2000, le=2100)
    teacher_id: str | None = None


class ProjectCreate(BaseModel):
    name: str
    code: str
    major_id: str
    lab_id: str | None = None
    duration: int = Field(60, ge=1)
    max_score: float = Field(100, gt=0)
    description: str | None = None


class ReferenceImageCreate(BaseModel):
    image_url: str
    label: str | None = None


def _schedule_value(setting: SystemSetting | None) -> dict:
    return setting.value if setting else {"enabled": True, "frequency_hours": 24, "hour": 2}


async def _read_sync_upload(file: UploadFile, db: AsyncSession) -> tuple[list[str], list[dict], list[dict]]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="当前支持 UTF-8 CSV 文件")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不得超过 20MB")
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        columns = [str(item).strip() for item in (reader.fieldnames or []) if item]
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=400, detail=f"CSV 解析失败：{exc}") from exc
    if not rows:
        raise HTTPException(status_code=400, detail="CSV 中没有数据")
    if len(rows) > 5000:
        raise HTTPException(status_code=400, detail="单次最多导入 5000 条记录")

    missing = {"source_record_id", "completed_at"} - set(columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"CSV 缺少必填字段：{'、'.join(sorted(missing))}")
    if not ({"student_no", "student_index"} & set(columns)):
        raise HTTPException(status_code=400, detail="CSV 需要 student_no（推荐）或 student_index 字段")
    if not ({"project_name", "project_code", "project_index"} & set(columns)):
        raise HTTPException(status_code=400, detail="CSV 需要 project_name（推荐）、project_code 或 project_index 字段")

    student_numbers = set((await db.execute(select(Student.student_no))).scalars().all())
    projects = list((await db.execute(select(TrainingProject))).scalars().all())
    project_codes = {
        str((item.scoring_rules or {}).get("code") or item.id)
        for item in projects
    }
    project_name_counts = {
        name: sum(1 for item in projects if item.name == name)
        for name in {item.name for item in projects}
    }
    errors: list[dict] = []
    for row_number, row in enumerate(rows, start=2):
        reasons: list[str] = []
        source_id = str(row.get("source_record_id") or "").strip()
        if not source_id:
            reasons.append("缺少实训记录编号")
        completed_at = str(row.get("completed_at") or "").strip()
        try:
            datetime.fromisoformat(completed_at)
        except ValueError:
            reasons.append("完成时间格式应为 YYYY-MM-DDTHH:MM:SS")

        student_no = str(row.get("student_no") or "").strip()
        student_index = str(row.get("student_index") or "").strip()
        if student_no:
            if student_no not in student_numbers:
                reasons.append("学号不存在")
        elif student_index:
            try:
                int(student_index)
            except ValueError:
                reasons.append("student_index 必须是整数")
        else:
            reasons.append("缺少学号或学生索引")

        project_name = str(row.get("project_name") or "").strip()
        project_code = str(row.get("project_code") or "").strip()
        project_index = str(row.get("project_index") or "").strip()
        if project_name:
            if project_name_counts.get(project_name, 0) == 0:
                reasons.append("项目名称不存在")
            elif project_name_counts.get(project_name, 0) > 1:
                reasons.append("项目名称不唯一，请改用 project_code")
        elif project_code:
            if project_code not in project_codes:
                reasons.append("项目编码不存在")
        elif project_index:
            try:
                int(project_index)
            except ValueError:
                reasons.append("project_index 必须是整数")
        else:
            reasons.append("缺少项目编码或项目索引")

        if reasons:
            errors.append({"row_number": row_number, "source_record_id": source_id or None, "reason": "；".join(reasons)})
    return columns, rows, errors


@router.get("/sync-schedule")
async def get_sync_schedule(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    setting = (await db.execute(select(SystemSetting).where(SystemSetting.key == "sync_schedule"))).scalar_one_or_none()
    latest = (await db.execute(select(MockSyncTask).order_by(MockSyncTask.started_at.desc()).limit(1))).scalar_one_or_none()
    return {**_schedule_value(setting), "last_run_at": latest.started_at if latest else None}


@router.put("/sync-schedule")
async def update_sync_schedule(
    payload: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    setting = (await db.execute(select(SystemSetting).where(SystemSetting.key == "sync_schedule"))).scalar_one_or_none()
    before = setting.value if setting else None
    value = payload.model_dump()
    if setting:
        setting.value = value
        setting.updated_by = admin.id
    else:
        setting = SystemSetting(key="sync_schedule", value=value, updated_by=admin.id)
        db.add(setting)
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="update_sync_schedule", object_type="system_setting", object_id="sync_schedule", before=before, after=value)
    await db.commit()
    return value


@router.post("/sync-import")
async def import_sync_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    columns, rows, errors = await _read_sync_upload(file, db)
    valid_count = len(rows) - len(errors)
    if valid_count <= 0:
        raise HTTPException(status_code=400, detail="CSV 没有可导入的有效记录，请先修正预览中的错误")

    imported_at = datetime.utcnow().isoformat()
    value = {
        "filename": file.filename,
        "row_count": len(rows),
        "columns": columns,
        "rows": rows,
        "imported_at": imported_at,
    }
    setting = (await db.execute(
        select(SystemSetting).where(SystemSetting.key == PENDING_SYNC_SETTING_KEY)
    )).scalar_one_or_none()
    before = None
    if setting:
        before = {
            "filename": setting.value.get("filename"),
            "row_count": setting.value.get("row_count"),
            "imported_at": setting.value.get("imported_at"),
        }
        setting.value = value
        setting.updated_by = admin.id
    else:
        db.add(SystemSetting(key=PENDING_SYNC_SETTING_KEY, value=value, updated_by=admin.id))
    await record_audit(
        db,
        actor_id=admin.id,
        actor_name=admin.name,
        action="stage_sync_import",
        object_type="sync_import",
        object_id=file.filename,
        before=before,
        after={"filename": file.filename, "row_count": len(rows), "imported_at": imported_at},
    )
    await db.commit()
    return {
        "status": "imported",
        "message": "导入数据成功",
        "filename": file.filename,
        "row_count": len(rows),
        "valid_count": valid_count,
        "error_count": len(errors),
        "imported_at": imported_at,
    }


@router.post("/sync-import/preview")
async def preview_sync_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    columns, rows, errors = await _read_sync_upload(file, db)
    invalid_rows = {item["row_number"] for item in errors}
    preview = []
    for row_number, row in enumerate(rows[:10], start=2):
        preview.append({
            "row_number": row_number,
            "source_record_id": row.get("source_record_id"),
            "student": row.get("student_no") or f"学生索引 {row.get('student_index', '—')}",
            "project": row.get("project_name") or row.get("project_code") or f"项目索引 {row.get('project_index', '—')}",
            "completed_at": row.get("completed_at"),
            "valid": row_number not in invalid_rows,
        })
    return {
        "filename": file.filename,
        "columns": columns,
        "row_count": len(rows),
        "valid_count": len(rows) - len(errors),
        "error_count": len(errors),
        "can_import": len(rows) > len(errors),
        "preview": preview,
        "errors": errors[:20],
    }


@router.get("/sync-import/template.csv")
async def download_sync_template(
    admin: User = Depends(get_current_admin),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["source_record_id", "student_no", "project_name", "completed_at"])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="training-record-import-template.csv"'},
    )


@router.get("/audit-logs")
async def list_audit_logs(
    actor_id: str | None = None,
    object_type: str | None = None,
    result: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = select(AuditLog)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    if result:
        query = query.where(AuditLog.result == result)
    rows = list((await db.execute(query.order_by(AuditLog.created_at.desc()).limit(limit))).scalars().all())
    return [{
        "id": item.id,
        "actor_id": item.actor_id,
        "actor_name": item.actor_name,
        "action": item.action,
        "object_type": item.object_type,
        "object_id": item.object_id,
        "result": item.result,
        "reason": item.reason,
        "before": item.before,
        "after": item.after,
        "created_at": item.created_at,
    } for item in rows]


def _sqlite_path() -> Path:
    prefix = "sqlite+aiosqlite:///"
    if not settings.DATABASE_URL.startswith(prefix):
        raise HTTPException(status_code=400, detail="当前数据库类型需由运维工具执行备份")
    return Path(settings.DATABASE_URL[len(prefix):]).resolve()


@router.post("/backups")
async def create_backup(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    source = _sqlite_path()
    if not source.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")
    target_dir = source.parent / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"training-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}.db"
    target = target_dir / filename
    source_conn = sqlite3.connect(source)
    target_conn = sqlite3.connect(target)
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    item = BackupRecord(filename=str(target), status="completed", size_bytes=target.stat().st_size, checksum=checksum, created_by=admin.id)
    db.add(item)
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="create_backup", object_type="backup", object_id=item.id, after={"filename": filename, "checksum": checksum})
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "filename": filename, "size_bytes": item.size_bytes, "checksum": checksum, "status": item.status, "created_at": item.created_at}


@router.get("/backups")
async def list_backups(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = list((await db.execute(select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(30))).scalars().all())
    return [{"id": item.id, "filename": Path(item.filename).name, "size_bytes": item.size_bytes, "checksum": item.checksum, "status": item.status, "created_at": item.created_at} for item in rows]


@router.post("/backups/{backup_id}/verify")
async def verify_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    item = (await db.execute(select(BackupRecord).where(BackupRecord.id == backup_id))).scalar_one_or_none()
    if not item or not Path(item.filename).exists():
        raise HTTPException(status_code=404, detail="备份不存在")
    with tempfile.TemporaryDirectory(prefix="shixun-restore-check-") as temp_dir:
        restored = Path(temp_dir) / "restored.db"
        shutil.copy2(item.filename, restored)
        connection = sqlite3.connect(restored)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("users", "students", "training_records", "scores")
            }
        finally:
            connection.close()
    ok = integrity == "ok"
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="verify_backup", object_type="backup", object_id=item.id, result="success" if ok else "failed", after={"integrity": integrity, "counts": counts})
    await db.commit()
    return {"verified": ok, "integrity": integrity, "counts": counts, "checksum_matches": hashlib.sha256(Path(item.filename).read_bytes()).hexdigest() == item.checksum}


@router.get("/status")
async def get_runtime_status(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    database_ok = (await db.execute(select(func.count()).select_from(User))).scalar() is not None
    latest_sync = (await db.execute(select(MockSyncTask).order_by(MockSyncTask.started_at.desc()).limit(1))).scalar_one_or_none()
    return {
        "application": {"status": "healthy", "version": settings.APP_VERSION},
        "database": {"status": "healthy" if database_ok else "failed", "type": settings.DATABASE_URL.split(":", 1)[0]},
        "sync": {"status": latest_sync.status.value if latest_sync else "not_run", "last_run_at": latest_sync.started_at if latest_sync else None},
        "ai": {"status": "configured" if settings.LLM_API_KEY else "not_configured", "provider": settings.LLM_PROVIDER, "model": settings.LLM_MODEL},
        "checked_at": datetime.utcnow(),
    }


@router.get("/performance-report")
async def get_performance_report(
    admin: User = Depends(get_current_admin),
):
    """返回最近一次脱敏的 50 并发只读工程验证结果（不在产品 UI 展示）。"""
    return {
        "id": "public-demo-readonly-20260926",
        "title": "50 并发只读工程验证",
        "environment": "公网 Demo（HTTPS）",
        "verified_at": datetime.fromisoformat("2026-09-26T21:49:59-07:00"),
        "source_commit": "ca22cde",
        "concurrent_users": 50,
        "duration_seconds": 34.264,
        "total_requests": 910,
        "successful_requests": 910,
        "failed_requests": 0,
        "success_rate": 100.0,
        "throughput_rps": 26.558,
        "request_method": "GET only",
        "basic": {
            "label": "常规查询",
            "requests": 632,
            "p50_seconds": 0.531,
            "p95_seconds": 1.617,
            "p99_seconds": 3.158,
            "target_seconds": 3.0,
            "passed": True,
        },
        "aggregate": {
            "label": "班级统计 / 能力汇总",
            "requests": 278,
            "p50_seconds": 2.219,
            "p95_seconds": 4.124,
            "p99_seconds": 5.221,
            "target_seconds": 10.0,
            "passed": True,
        },
        "passed": True,
        "note": "Demo 工程验证，不替代正式验收。正式验收须由双方确认测试环境、标准业务脚本、原始日志和汇总报告。",
    }


@router.get("/accounts")
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = list((await db.execute(select(User).order_by(User.role, User.username))).scalars().all())
    return [{"id": item.id, "username": item.username, "name": item.name, "role": item.role.value, "created_at": item.created_at} for item in rows]


@router.post("/accounts")
async def create_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if settings.RELEASE_MODE and len(payload.password)<12:
        raise HTTPException(400,"校内账号密码至少 12 位，请使用上线管理配置")
    if (await db.execute(select(User.id).where(User.username == payload.username))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="账号已存在")
    item = User(id=str(uuid.uuid4()), username=payload.username, name=payload.name, role=payload.role, password_hash=AuthService.get_password_hash(payload.password))
    db.add(item)
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="create_account", object_type="user", object_id=item.id, after={"username": item.username, "name": item.name, "role": item.role.value})
    await db.commit()
    return {"id": item.id, "username": item.username, "name": item.name, "role": item.role.value}


@router.get("/classes")
async def list_classes(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = list((await db.execute(select(Class).order_by(Class.year.desc(), Class.name))).scalars().all())
    counts = dict((await db.execute(select(Student.class_id, func.count(Student.id)).group_by(Student.class_id))).all())
    return [{"id": item.id, "name": item.name, "major_id": item.major_id, "teacher_id": item.teacher_id, "year": item.year, "student_count": counts.get(item.id, 0)} for item in rows]


@router.post("/classes")
async def create_class(
    payload: ClassCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not (await db.execute(select(Major.id).where(Major.id == payload.major_id))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="专业不存在")
    if payload.teacher_id and not (await db.execute(select(User.id).where(User.id == payload.teacher_id, User.role == UserRole.TEACHER))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="教师账号不存在")
    item = Class(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(item)
    if payload.teacher_id:
        db.add(TeacherClassAssignment(teacher_id=payload.teacher_id, class_id=item.id))
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="create_class", object_type="class", object_id=item.id, after=payload.model_dump())
    await db.commit()
    return {"id": item.id, **payload.model_dump()}


@router.get("/projects")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = list((await db.execute(select(TrainingProject).order_by(TrainingProject.name))).scalars().all())
    return [{
        "id": item.id,
        "name": item.name,
        "code": (item.scoring_rules or {}).get("code"),
        "major_id": item.major_id,
        "lab_id": item.lab_id,
        "duration": item.duration,
        "max_score": item.max_score,
        "enabled": (item.scoring_rules or {}).get("enabled", True),
        "repeat_policy": (item.scoring_rules or {}).get("repeat_policy", "keep_all"),
        "description": (item.scoring_rules or {}).get("description"),
        "steps": item.steps or [],
    } for item in rows]


@router.post("/projects")
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not (await db.execute(select(Major.id).where(Major.id == payload.major_id))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="专业不存在")
    item = TrainingProject(
        id=str(uuid.uuid4()),
        name=payload.name,
        major_id=payload.major_id,
        lab_id=payload.lab_id,
        duration=payload.duration,
        max_score=payload.max_score,
        steps=[],
        ability_mapping={},
        scoring_rules={"version": 1, "code": payload.code, "description": payload.description, "enabled": True, "repeat_policy": "keep_all"},
    )
    db.add(item)
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="create_project", object_type="training_project", object_id=item.id, after=payload.model_dump())
    await db.commit()
    return {"id": item.id, **payload.model_dump(), "enabled": True, "repeat_policy": "keep_all", "steps": []}


@router.get("/labs/{lab_id}/reference-images")
async def list_reference_images(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = list((await db.execute(select(ReferenceImage).where(ReferenceImage.lab_id == lab_id).order_by(ReferenceImage.created_at))).scalars().all())
    return [{"id": item.id, "lab_id": item.lab_id, "image_url": item.image_url, "label": item.label, "enabled": item.enabled, "created_at": item.created_at} for item in rows]


@router.post("/labs/{lab_id}/reference-images")
async def create_reference_image(
    lab_id: str,
    payload: ReferenceImageCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    item = ReferenceImage(id=str(uuid.uuid4()), lab_id=lab_id, image_url=payload.image_url, label=payload.label, created_by=admin.id)
    db.add(item)
    await record_audit(db, actor_id=admin.id, actor_name=admin.name, action="create_reference_image", object_type="lab", object_id=lab_id, after=payload.model_dump())
    await db.commit()
    return {"id": item.id, "lab_id": lab_id, **payload.model_dump(), "enabled": True}
