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
from sqlalchemy import select
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


@router.get("/catalog/{kind}")
async def catalog_list(kind: str, limit: int=Query(1000,ge=1,le=5000), offset:int=Query(0,ge=0), db=Depends(get_db)):
    if kind not in CATALOG:
        raise HTTPException(404,"数据类型不存在")
    model,fields,required=CATALOG[kind]
    items=(await db.execute(select(model).order_by(model.id).offset(offset).limit(limit))).scalars().all()
    rows=[]
    for item in items:
        rows.append({**as_dict(item,fields),**(await setting(db,f"state:{kind}:{item.id}",{}))})
    return {"fields":fields,"required":required,"items":rows}


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
    from app.services.audit import record_audit
    before=await setting(db,"release:source",{})
    await put_setting(db,"release:source",data.model_dump(),admin.id)
    await record_audit(db,actor_id=admin.id,actor_name=admin.name,action="configure_source",object_type="source",before=before,after=data.model_dump())
    await db.commit()
    return {"saved":True}


@router.post("/source/sync")
async def source_sync(admin=Depends(get_current_admin)):
    try:
        async with worker.lock:
            return await worker.sync_source(force=True,actor=admin)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc


@router.post("/records/import")
async def import_records(file:UploadFile=File(...),source:str="school-file",admin=Depends(get_current_admin),db=Depends(get_db)):
    try:
        rows=parse_upload(file.filename or "",await file.read(20*1024*1024+1))
        task=await ProductionIngest(db).run(rows,actor_id=admin.id,actor_name=admin.name,source=source)
    except (ValueError,UnicodeError) as exc:
        raise HTTPException(400,str(exc)) from exc
    return {"task_id":task.id,"read":task.read_count,"success":task.success_count,"skipped":task.skipped_count,"errors":task.error_count}


@router.post("/exceptions/{exception_id}/retry")
async def retry_exception(exception_id:str,source:str="school-file",data:dict|None=None,admin=Depends(get_current_admin),db=Depends(get_db)):
    item=await db.get(MockSyncException,exception_id)
    if not item:
        raise HTTPException(404)
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
        query=query.where(AuditLog.created_at>=date_from)
    if date_to:
        query=query.where(AuditLog.created_at<=date_to)
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
