import asyncio
import hashlib
import io
import json
import logging
import os
import sqlite3
import tarfile
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import select, delete, text

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.operations import AuditLog, SystemSetting
from app.models.workflow import ReportTask, EnvironmentTask, TaskStatus, MockSyncTask, MockSyncException
from app.models.user import User, UserRole
from app.services.production_data import setting, put_setting, ProductionIngest, read_mysql

logger = logging.getLogger("shixun.operations")
METRICS = {"requests":0,"errors":0,"latency_seconds":0.0}


def backup_database(destination=None):
    if not settings.DATABASE_URL.startswith("sqlite+aiosqlite:///"):
        raise ValueError("单镜像备份工具仅支持 SQLite")
    key = os.getenv("BACKUP_ENCRYPTION_KEY", "")
    cipher = Fernet(key.encode())
    source = Path(settings.DATABASE_URL.removeprefix("sqlite+aiosqlite:///")).resolve()
    dest = Path(destination or os.getenv("BACKUP_DIR","/backups"))
    dest.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        snapshot = Path(temp)/"training.db"
        with sqlite3.connect(source) as live, sqlite3.connect(snapshot) as target:
            live.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("备份完整性校验失败")
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer,mode="w:gz") as archive:
            archive.add(snapshot,arcname="training.db")
            uploads = source.parent/"uploads"
            config_keys={"SECRET_KEY","DEPLOYMENT_MODE","RELEASE_MODE","DEBUG","AUDIT_RETENTION_DAYS","BACKUP_RETENTION_DAYS","CAMERA_ALLOWED_HOSTS","AI_FALLBACK_ROUTES","ALLOW_LOCAL_AI_HTTP"}
            config_values={k:v for k,v in os.environ.items() if k in config_keys or k.startswith(("SCHOOL_DB_","OIDC_","LLM_","VLM_"))}
            config_payload=json.dumps(config_values).encode()
            config_info=tarfile.TarInfo("runtime-config.json")
            config_info.size=len(config_payload)
            archive.addfile(config_info,io.BytesIO(config_payload))
            if uploads.exists():
                archive.add(uploads,arcname="uploads")
            manifest = json.dumps({"format":1,"created_at":datetime.utcnow().isoformat(),"app_version":settings.APP_VERSION,
                                   "database_sha256":hashlib.sha256(snapshot.read_bytes()).hexdigest()}).encode()
            info = tarfile.TarInfo("manifest.json")
            info.size = len(manifest)
            archive.addfile(info,io.BytesIO(manifest))
        target = dest/f"backup-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}.enc"
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(cipher.encrypt(buffer.getvalue()))
        temporary.chmod(0o600)
        temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".sha256").write_text(digest+"  "+target.name+"\n")
    retention=max(7,int(os.getenv("BACKUP_RETENTION_DAYS","30")))
    for old in dest.glob("backup-*.enc"):
        if old != target and old.stat().st_mtime < time.time()-retention*86400:
            old.unlink()
            old.with_suffix(".sha256").unlink(missing_ok=True)
    return {"filename":target.name,"sha256":digest,"size":target.stat().st_size}


def restore_to_new_directory(backup, destination, key):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("恢复目标必须为空目录；禁止覆盖运行中的数据库")
    destination.mkdir(parents=True,exist_ok=True)
    payload = Fernet(key.encode()).decrypt(Path(backup).read_bytes())
    with tarfile.open(fileobj=io.BytesIO(payload),mode="r:gz") as archive:
        for member in archive.getmembers():
            path = (destination/member.name).resolve()
            if not path.is_relative_to(destination.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError("备份中存在非法路径或链接")
        archive.extractall(destination)
    manifest = json.loads((destination/"manifest.json").read_text())
    restored = destination/"training.db"
    if hashlib.sha256(restored.read_bytes()).hexdigest()!=manifest["database_sha256"]:
        raise ValueError("数据库校验和不匹配")
    with sqlite3.connect(restored) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("恢复数据库完整性检查失败")
        counts = {table:db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("users","students","scores")}
    return {"verified":True,"counts":counts}


class OperationalMiddleware:
    def __init__(self, app):
        self.app=app

    async def __call__(self, scope, receive, send):
        if scope["type"]!="http":
            return await self.app(scope,receive,send)
        started, status, request_id = time.monotonic(),500,uuid.uuid4().hex
        path, method = scope["path"],scope["method"]
        async def wrapped(message):
            nonlocal status
            if message["type"]=="http.response.start":
                status=message["status"]
                message.setdefault("headers",[]).extend([(b"x-request-id",request_id.encode()),(b"x-content-type-options",b"nosniff"),(b"referrer-policy",b"same-origin")])
            await send(message)
        try:
            await self.app(scope,receive,wrapped)
        finally:
            elapsed=time.monotonic()-started
            METRICS["requests"]+=1
            METRICS["errors"]+=int(status>=500)
            METRICS["latency_seconds"]+=elapsed
            logger.info(json.dumps({"event":"http","request_id":request_id,"path":path,"method":method,"status":status,"seconds":round(elapsed,4)}))
            if path.startswith("/api/") and (method not in {"GET","HEAD","OPTIONS"} or "export" in path or "download" in path):
                try:
                    from app.services.auth import AuthService
                    actor=None
                    token=dict(scope.get("headers",[])).get(b"authorization",b"").decode().removeprefix("Bearer ")
                    try:
                        actor=AuthService.decode_token(token).user_id
                    except Exception:
                        pass
                    async with AsyncSessionLocal() as db:
                        await db.execute(text("BEGIN IMMEDIATE"))
                        if actor and not await db.get(User,actor):
                            actor=None
                        db.add(AuditLog(actor_id=actor,action=method,object_type="api",object_id=path[:100],
                            result="success" if status<400 else "failed",reason=None if status<400 else str(status),
                            after={"request_id":request_id,"ip":scope.get("client",[None])[0],"status":status}))
                        await db.commit()
                except Exception:
                    logger.exception("audit_persistence_failed request_id=%s",request_id)


class ReleaseWorker:
    def __init__(self):
        self.task=None
        self.lock=asyncio.Lock()

    async def start(self):
        # Single worker process. Interrupted work becomes explicitly retryable,
        # never silently reported as completed.
        async with AsyncSessionLocal() as db:
            for model in (ReportTask,EnvironmentTask,MockSyncTask):
                rows=(await db.execute(select(model).where(model.status==TaskStatus.RUNNING))).scalars().all()
                for row in rows:
                    row.status=TaskStatus.FAILED
                    if model is MockSyncTask:
                        db.add(MockSyncException(task_id=row.id,row_number=0,source_record_id=None,reason="服务重启中断；已提交行保留，重新同步会自动去重",raw_data={}))
                    else:
                        row.error_message="服务重启中断；请重新提交任务"
                    row.completed_at=datetime.utcnow()
            await db.commit()
        self.task=asyncio.create_task(self.run())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def tick(self):
        from app.services.report import process_report_task
        from app.services.environment import process_environment_task
        async with self.lock:
            async with AsyncSessionLocal() as db:
                jobs=[]
                for model,processor in ((ReportTask,process_report_task),(EnvironmentTask,process_environment_task)):
                    ids=(await db.execute(select(model.id).where(model.status==TaskStatus.PENDING).order_by(model.created_at).limit(2))).scalars().all()
                    jobs.extend(processor(i) for i in ids)
            if jobs:
                await asyncio.gather(*jobs)
            now=datetime.utcnow()
            async with AsyncSessionLocal() as db:
                last=await setting(db,"release:last_backup",{})
            # Do not retain a read snapshot while a backup/import writes. In WAL
            # mode upgrading that stale snapshot fails immediately, even with a
            # busy timeout. Acquire the write transaction before reading settings.
            backup_result=None
            backup_failed=False
            if os.getenv("BACKUP_ENCRYPTION_KEY") and (not last.get("time") or now-datetime.fromisoformat(last["time"])>=timedelta(days=1)):
                try:
                    backup_result=await asyncio.to_thread(backup_database)
                except Exception:
                    backup_failed=True
                    logger.exception("scheduled_backup_failed")
            async with AsyncSessionLocal() as db:
                await db.execute(text("BEGIN IMMEDIATE"))
                if backup_result is not None:
                    await put_setting(db,"release:last_backup",{"time":now.isoformat(),"status":"completed",**backup_result})
                    await put_setting(db,"release:backup_error",{})
                elif backup_failed:
                    await put_setting(db,"release:backup_error",{"time":now.isoformat(),"status":"failed"})
                retention=max(180,int(os.getenv("AUDIT_RETENTION_DAYS","180")))
                await db.execute(delete(AuditLog).where(AuditLog.created_at<now-timedelta(days=retention)))
                await put_setting(db,"release:worker",{"heartbeat":now.isoformat(),"status":"running"})
                await db.commit()
            await self.sync_source()

    async def sync_source(self, force=False, actor=None):
        async with AsyncSessionLocal() as db:
            cfg=await setting(db,"release:source",{})
            last=await setting(db,"release:last_sync",{})
            now=datetime.utcnow()
            if not cfg.get("enabled") and not force:
                return
            if not cfg.get("fields"):
                if force:
                    raise ValueError("尚未配置校方数据源")
                return
            if not force and cfg.get("hour") is not None and not last.get("backlog"):
                local=now+timedelta(hours=8)
                scheduled=local.replace(hour=int(cfg["hour"]),minute=0,second=0,microsecond=0)
                if local < scheduled and not last.get("time"):
                    return
            hours=max(1,float(cfg.get("frequency_hours",24)))
            if not force and not last.get("backlog") and last.get("time") and now-datetime.fromisoformat(last["time"])<timedelta(hours=hours):
                return
            admin=actor or (await db.execute(select(User).where(User.role==UserRole.ADMIN).limit(1))).scalar_one_or_none()
            if not admin:
                return
            credentials={k:os.getenv("SCHOOL_DB_"+k.upper(),"") for k in ("host","port","user","password","database","ssl_ca")}
            credentials["port"]=credentials["port"] or 3306
            try:
                cursor=last.get("cursor")
                totals={"read":0,"success":0,"errors":0,"skipped":0,"task_ids":[]}
                # Drain pages, checkpoint each one; a bounded run resumes without
                # waiting another full interval if a large backlog remains.
                limit=min(max(int(cfg.get("batch_size",1000)),1),5000)
                more=False
                for _ in range(100):
                    rows=await asyncio.to_thread(read_mysql,cfg,credentials,cursor)
                    task=await ProductionIngest(db).run(rows,actor_id=admin.id,actor_name=admin.name,source=cfg.get("source","school"))
                    new_cursor=[rows[-1]["updated_at"],rows[-1]["source_record_id"]] if rows else cursor
                    if rows and new_cursor==cursor:
                        raise ValueError("校方增量游标没有推进")
                    cursor=new_cursor
                    more=len(rows)==limit
                    totals["task_ids"].append(task.id)
                    for name in ("read","success","errors","skipped"):
                        totals[name]+=getattr(task,{"read":"read_count","success":"success_count","errors":"error_count","skipped":"skipped_count"}[name])
                    await put_setting(db,"release:last_sync",{"time":now.isoformat(),"cursor":cursor,"status":"completed","task_id":task.id,"backlog":more})
                    await put_setting(db,"release:last_sync_error",{})
                    await db.commit()
                    if not more:
                        break
                return {"task_id":task.id,**totals,"backlog":more}
            except Exception as exc:
                await db.rollback()
                await put_setting(db,"release:last_sync_error",{"time":now.isoformat(),"status":"failed","reason":type(exc).__name__})
                await db.commit()
                if force:
                    raise ValueError("数据源同步失败，请检查映射、网络和只读账号；详见服务器日志") from exc
                logger.exception("source_sync_failed")

    async def run(self):
        while True:
            try:
                await self.tick()
            except Exception:
                logger.exception("release_worker_failed")
            await asyncio.sleep(5)


worker=ReleaseWorker()
