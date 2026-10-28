from app.services.time_utils import utc_boundary
"""On-prem implementation and administration APIs."""
import asyncio
import csv
import io
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.adapters.controllers.auth import get_current_admin
from app.database import get_db
from app.models.operations import AuditLog, ConfigurationVersion, ReferenceImage
from app.models.lab import Lab
from app.models.workflow import MockSyncException
from app.services.catalog import CATALOG, as_dict, save_item, parse_upload
from app.services.production_data import setting, put_setting, ProductionIngest, identifier
from app.services.operations_runtime import METRICS, worker, backup_database

router=APIRouter(prefix="/api/v1/release",tags=["校内部署管理"],dependencies=[Depends(get_current_admin)])


class SourceConfig(BaseModel):
    enabled: bool=False
    source: str=Field(default="school",min_length=1,max_length=40)
    table: str
    fields: dict[str,str]
    frequency_hours: int=Field(default=24,ge=1,le=24)
    batch_size: int=Field(default=1000,ge=1,le=5000)
    hour: int|None=Field(default=None,ge=0,le=23)


@router.get("/catalog/{kind}")
async def catalog_list(kind: str, limit: int=Query(1000,ge=1,le=5000), offset:int=Query(0,ge=0), db=Depends(get_db)):
    if kind not in CATALOG:
        raise HTTPException(404,"数据类型不存在")
    model,fields,required=CATALOG[kind]
    items=(await db.execute(select(model).order_by(model.id).offset(offset).limit(limit))).scalars().all()
    rows=[]
    for item in items:
        rows.append({**as_dict(item,fields),**(await setting(db,f"state:{kind}:{item.id}",{}))})
    return {"fields":fields+(["code"] if kind in {"abilities","sub-abilities"} else ["code","description"] if kind=="projects" else []),"required":required,"items":rows}


@router.post("/catalog/{kind}")
async def create(kind: str, data:dict, admin=Depends(get_current_admin), db=Depends(get_db)):
    try:
        result=await save_item(db,kind,data,admin)
        await db.commit()
        return result
    except (ValueError,TypeError,IntegrityError) as exc:
        await db.rollback()
        raise HTTPException(400,str(exc) if not isinstance(exc,IntegrityError) else "数据唯一性或关联校验失败") from exc


@router.put("/catalog/{kind}/{item_id}")
async def update(kind: str,item_id:str,data:dict,admin=Depends(get_current_admin),db=Depends(get_db)):
    if kind=="accounts" and item_id==admin.id and (data.get("enabled") is False or data.get("role","admin")!="admin"):
        raise HTTPException(400,"不能停用或降级当前管理员账号")
    try:
        result=await save_item(db,kind,data,admin,item_id)
        await db.commit()
        return result
    except (ValueError,TypeError,IntegrityError) as exc:
        await db.rollback()
        raise HTTPException(400,str(exc) if not isinstance(exc,IntegrityError) else "数据唯一性或关联校验失败") from exc


@router.post("/catalog/{kind}/import")
async def import_catalog(kind:str,file:UploadFile=File(...),preview:bool=False,admin=Depends(get_current_admin),db=Depends(get_db)):
    try:
        rows=parse_upload(file.filename or "",await file.read(20*1024*1024+1))
    except (ValueError,UnicodeError,StopIteration) as exc:
        raise HTTPException(400,str(exc)) from exc
    if db.bind.dialect.name=="sqlite":
        await db.commit()
        await db.execute(text("BEGIN IMMEDIATE"))
    results=[]
    for index,row in enumerate(rows,2):
        row={key:value for key,value in row.items() if value is not None and value!=""}
        try:
            async with db.begin_nested() as transaction:
                item_id=row.pop("id",None)
                result=await save_item(db,kind,row,admin,item_id)
                if preview:
                    await transaction.rollback()
            results.append({"row":index,"status":"valid" if preview else "success","id":result["id"]})
        except (ValueError,TypeError,IntegrityError) as exc:
            results.append({"row":index,"status":"error","reason":str(exc) if not isinstance(exc,IntegrityError) else "唯一性或关联校验失败"})
    await db.commit()
    return {"preview":preview,"total":len(rows),"success":sum(x["status"]!="error" for x in results),"results":results}


@router.get("/templates/{kind}.csv")
async def template(kind:str):
    if kind=="records":
        fields=["source_record_id","student_no","project_code","completed_at","steps","environment_image"]
    elif kind in CATALOG:
        fields=CATALOG[kind][1]+(["password"] if kind=="accounts" else [])+["enabled"]
    else:
        raise HTTPException(404)
    return Response("\ufeff"+",".join(fields)+"\n",media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="{kind}-template.csv"'})


@router.get("/source")
async def source_get(db=Depends(get_db)):
    return {"config":await setting(db,"release:source",{}),"last_run":await setting(db,"release:last_sync",{}),
            "last_error":await setting(db,"release:last_sync_error",{}),"credentials_configured":all(os.getenv("SCHOOL_DB_"+k) for k in ("HOST","USER","PASSWORD","DATABASE"))}


@router.put("/source")
async def source_put(data:SourceConfig,admin=Depends(get_current_admin),db=Depends(get_db)):
    try:
        identifier(data.table)
        for field in data.fields.values():
            identifier(field)
        if not {"source_record_id","student_no","project_code","completed_at","steps","updated_at"}.issubset(data.fields):
            raise ValueError("缺少源记录标识、学号、项目、时间、步骤 JSON 或更新时间映射")
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    async with worker.lock:
        from app.services.audit import record_audit
        before=await setting(db,"release:source",{})
        if any(before.get(key)!=data.model_dump().get(key) for key in ("source","table","fields")):
            await put_setting(db,"release:last_sync",{})
        await put_setting(db,"release:source",data.model_dump(),admin.id)
        await record_audit(db,actor_id=admin.id,actor_name=admin.name,action="configure_source",object_type="source",before=before,after=data.model_dump())
        await db.commit()
        return {"saved":True}


@router.post("/source/sync")
async def source_sync(full:bool=False,admin=Depends(get_current_admin)):
    try:
        async with worker.lock:
            if full:
                return await worker.sync_source(force=True,actor=admin,reset_cursor=True)
            return await worker.sync_source(force=True,actor=admin)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc


@router.get("/source/evidence")
async def source_evidence(db=Depends(get_db)):
    """Actual source metadata and persisted provenance; never returns credentials."""
    from app.services.mysql_evidence import inspect_source
    from app.models.training import TrainingRecord, Score
    from app.models.operations import SystemSetting
    cfg=await setting(db,"release:source",{})
    if not cfg.get('fields'):
        raise HTTPException(400,"请先保存数据源映射")
    try:
        probe=await asyncio.to_thread(inspect_source,cfg)
    except Exception as exc:
        raise HTTPException(400,"MySQL 检查失败，请核对连接和只读权限") from exc
    records=[]
    rows=(await db.execute(select(TrainingRecord,Score,SystemSetting).join(Score,Score.record_id==TrainingRecord.id)
        .join(SystemSetting,SystemSetting.key==('source:'+TrainingRecord.id))
        .where(SystemSetting.value['source'].as_string()==cfg.get('source','school'))
        .order_by(TrainingRecord.completed_at.desc(),TrainingRecord.id).limit(12))).all()
    for record,score,provenance in rows:
        evidence=provenance.value
        if evidence:
            records.append({"record_id":record.id,"score_id":score.id,"score":score.total_score,"max_score":score.max_score,
                            "source":evidence.get('source'),"source_record_id":evidence.get('source_record_id'),
                            "batch_id":evidence.get('batch_id'),"completed_at":evidence.get('completed_at'),"class_name":evidence.get('class_name')})
    return {"source_database":probe,"business_database":db.bind.dialect.name,"records":records,
            "last_run":await setting(db,'release:last_sync',{}),"last_error":await setting(db,'release:last_sync_error',{})}


@router.post("/backups/verify")
async def verify_backup(db=Depends(get_db)):
    from app.services.operations_runtime import restore_to_new_directory
    from pathlib import Path
    import tempfile
    last=await setting(db,'release:last_backup',{})
    if not last.get('filename'):
        raise HTTPException(400,'请先创建加密备份')
    def verify():
        with tempfile.TemporaryDirectory(prefix='shixun-restore-') as dest:
            result=restore_to_new_directory(Path(os.getenv('BACKUP_DIR','/backups'))/last['filename'],dest,os.environ['BACKUP_ENCRYPTION_KEY'])
            restored=json.loads((Path(dest)/'runtime-config.json').read_text())
            if any(os.getenv(key)!=value for key,value in restored.items()):
                raise ValueError('恢复的系统配置与备份时配置不一致')
            import sqlite3
            with sqlite3.connect(Path(dest)/'training.db') as check:
                if check.execute('PRAGMA foreign_key_check').fetchall():
                    raise ValueError('恢复数据库外键核验失败')
            return {**result,'configuration_verified':True,'configuration_entries':len(restored),'foreign_keys_verified':True}
    result=await asyncio.to_thread(verify)
    result.update({'time':datetime.utcnow().isoformat(),'filename':last['filename'],'mode':'独立临时目录恢复，不覆盖运行库'})
    await put_setting(db,'release:last_restore',result)
    await db.commit()
    return result


@router.post("/records/import")
async def import_records(file:UploadFile=File(...),source:str="school-file",admin=Depends(get_current_admin),db=Depends(get_db)):
    try:
        rows=parse_upload(file.filename or "",await file.read(20*1024*1024+1))
        task=await ProductionIngest(db).run(rows,actor_id=admin.id,actor_name=admin.name,source=source)
    except (ValueError,UnicodeError) as exc:
        raise HTTPException(400,str(exc)) from exc
    return {"task_id":task.id,"read":task.read_count,"success":task.success_count,"skipped":task.skipped_count,"errors":task.error_count}


@router.post("/exceptions/{exception_id}/retry")
async def retry_exception(exception_id:str,source:str|None=None,data:dict|None=None,admin=Depends(get_current_admin),db=Depends(get_db)):
    item=await db.get(MockSyncException,exception_id)
    if not item:
        raise HTTPException(404)
    source=source or (await setting(db,"sync_task_source:"+item.task_id,{})).get("source","school-file")
    task=await ProductionIngest(db).run([data or item.raw_data],actor_id=admin.id,actor_name=admin.name,source=source)
    return {"task_id":task.id,"success":task.success_count,"errors":task.error_count,"skipped":task.skipped_count}


@router.get("/audit")
async def audit(actor_id:str|None=None,object_type:str|None=None,result:str|None=None,date_from:datetime|None=None,date_to:datetime|None=None,
                limit:int=Query(100,ge=1,le=1000),offset:int=Query(0,ge=0),db=Depends(get_db)):
    query=select(AuditLog)
    for column,value in [(AuditLog.actor_id,actor_id),(AuditLog.object_type,object_type),(AuditLog.result,result)]:
        if value:
            query=query.where(column==value)
    if date_from:
        query=query.where(AuditLog.created_at>=utc_boundary(date_from))
    if date_to:
        query=query.where(AuditLog.created_at<=utc_boundary(date_to))
    rows=(await db.execute(query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return [{c.name:getattr(row,c.name) for c in AuditLog.__table__.columns} for row in rows]


@router.get("/versions/{kind}/{item_id}")
async def versions(kind:str,item_id:str,db=Depends(get_db)):
    rows=(await db.execute(select(ConfigurationVersion).where(ConfigurationVersion.object_type==kind,ConfigurationVersion.object_id==item_id).order_by(ConfigurationVersion.version.desc()))).scalars().all()
    return [{"version":x.version,"before":x.before,"after":x.after,"changed_by":x.changed_by,"changed_at":x.changed_at} for x in rows]


@router.get("/status")
async def runtime_status(db=Depends(get_db)):
    from sqlalchemy import text
    await db.execute(text("SELECT 1"))
    heartbeat=await setting(db,"release:worker",{})
    stale=not heartbeat.get("heartbeat") or (datetime.utcnow()-datetime.fromisoformat(heartbeat["heartbeat"])).total_seconds()>180
    return {"database":"connected","worker":{**heartbeat,"stale":stale},"last_backup":await setting(db,"release:last_backup",{}),
            "backup_error":await setting(db,"release:backup_error",{}),"sync_error":await setting(db,"release:last_sync_error",{}),
            "ai":"configured-not-probed" if os.getenv("LLM_API_KEY") else "not_configured","metrics":METRICS}


@router.get("/metrics")
async def metrics():
    return Response("\n".join(f"shixun_{key} {value}" for key,value in METRICS.items())+"\n",media_type="text/plain")


@router.post("/backups")
async def backup(db=Depends(get_db)):
    try:
        result=await asyncio.to_thread(backup_database)
        await put_setting(db,"release:last_backup",{"time":datetime.utcnow().isoformat(),"status":"completed",**result})
        await db.commit()
        return result
    except (ValueError,TypeError) as exc:
        raise HTTPException(400,"请先配置有效的备份加密密钥和备份目录") from exc


@router.post("/labs/{lab_id}/reference")
async def upload_reference(lab_id:str,file:UploadFile=File(...),admin=Depends(get_current_admin),db=Depends(get_db)):
    import base64
    from app.services.images import validate_bytes
    lab=await db.get(Lab,lab_id)
    if not lab:
        raise HTTPException(404)
    content=await file.read(10*1024*1024+1)
    try:
        mime=validate_bytes(content)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    image="data:"+mime+";base64,"+base64.b64encode(content).decode()
    db.add(ReferenceImage(lab_id=lab_id,image_url=image,label=file.filename,created_by=admin.id))
    lab.reference_image_url=image
    await db.commit()
    return {"saved":True,"lab_id":lab_id}


@router.post("/connectivity")
async def connectivity(db=Depends(get_db)):
    """Read-only network probes; never trigger a paid model generation."""
    import httpx
    import time
    from app.config import settings
    from app.services.production_data import read_mysql
    results={"database":"connected"}
    if settings.LLM_API_KEY:
        started=time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10,follow_redirects=False) as client:
                response=await client.get(settings.LLM_BASE_URL.rstrip('/')+'/models',headers={"Authorization":"Bearer "+settings.LLM_API_KEY})
                response.raise_for_status()
            results['ai']={"reachable":True,"seconds":round(time.monotonic()-started,3),"note":"仅验证模型列表接口，不代表推理质量已验收"}
        except httpx.HTTPError:
            results['ai']={"reachable":False,"note":"检查出口、证书、接口地址及供应商凭据"}
    else:
        results['ai']={"reachable":False,"note":"未配置"}
    cfg=await setting(db,'release:source',{})
    if cfg.get('fields'):
        credentials={k:os.getenv('SCHOOL_DB_'+k.upper(),'') for k in ('host','port','user','password','database','ssl_ca')}
        credentials['port']=credentials['port'] or 3306
        try:
            await asyncio.to_thread(read_mysql,{**cfg,'batch_size':1},credentials)
            results['school_database']={"reachable":True}
        except Exception:
            results['school_database']={"reachable":False,"note":"检查校方只读账号、网段和字段映射"}
    else:
        results['school_database']={"reachable":False,"note":"未配置"}
    await put_setting(db,'release:connectivity',{'time':datetime.utcnow().isoformat(),**results})
    await db.commit()
    return results


@router.put('/references/{reference_id}')
async def reference_state(reference_id:str,data:dict,admin=Depends(get_current_admin),db=Depends(get_db)):
    from app.services.production_data import truth
    from app.services.audit import record_audit
    reference=await db.get(ReferenceImage,reference_id)
    if not reference:raise HTTPException(404,'参考图片不存在')
    try:active=truth(data.get('enabled'))
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    before={'enabled':reference.enabled,'label':reference.label}
    reference.enabled=active
    if 'label' in data:reference.label=str(data['label'])[:200]
    await record_audit(db,actor_id=admin.id,actor_name=admin.name,action='reference_state',object_type='reference',object_id=reference_id,before=before,after={'enabled':active,'label':reference.label})
    await db.commit()
    return {'id':reference_id,'enabled':active,'label':reference.label}
