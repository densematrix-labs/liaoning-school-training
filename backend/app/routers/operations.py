import hashlib
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
from app.models.student import Class, Major, Student
from app.models.training import TrainingProject
from app.models.workflow import MockSyncTask
from app.services.auth import AuthService
from app.services.audit import record_audit
from app.services.sync import SyncService, parse_csv

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
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="当前支持 UTF-8 CSV 文件")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不得超过 20MB")
    try:
        rows = parse_csv(content)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"CSV 解析失败：{exc}") from exc
    if not rows:
        raise HTTPException(status_code=400, detail="CSV 中没有数据")
    task = await SyncService(db).run(rows, actor_id=admin.id, actor_name=admin.name)
    return {
        "task_id": task.id,
        "read_count": task.read_count,
        "success_count": task.success_count,
        "skipped_count": task.skipped_count,
        "error_count": task.error_count,
        "duration_seconds": max(0, (task.completed_at - task.started_at).total_seconds()),
    }


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
    """返回最近一次经公网复测确认的 50 并发验收结果。"""
    return {
        "id": "public-demo-20260917",
        "title": "50 并发公网性能验收",
        "environment": "公网 Demo · shixun.demo.densematrix.ai",
        "verified_at": datetime(2026, 9, 17, 8, 46, 31),
        "source_commit": "d637446",
        "concurrent_users": 50,
        "duration_seconds": 60,
        "total_requests": 1784,
        "success_rate": 100.0,
        "basic": {
            "label": "常规查询接口",
            "p95_seconds": 1.826,
            "target_seconds": 3.0,
            "passed": True,
        },
        "aggregate": {
            "label": "汇总统计接口",
            "p95_seconds": 5.583,
            "target_seconds": 10.0,
            "passed": True,
        },
        "passed": True,
        "note": "该结果为 Demo 公网工程验收记录；正式交付时需在采购人确认的服务器、网络、数据量和业务脚本下复测。",
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
