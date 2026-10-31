from app.config import settings
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.environment import EnvironmentCheckService, process_environment_task
from app.schemas.auth import UserResponse
from app.schemas.lab import EnvironmentCheckRequest, EnvironmentCheckResponse, EnvironmentReviewRequest, EnvironmentTaskResponse, LabResponse
from app.models.lab import EnvironmentCheck, Lab
from app.routers.permissions import require_student_access

router = APIRouter(prefix="/api/v1/environment", tags=["环境检查"])


@router.get('/tasks')
async def query_environment_tasks(student_id: str, status: str = None, task_id: str = None,
    date_from: str = None, date_to: str = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    current_user: UserResponse = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    from sqlalchemy import func
    from app.models.workflow import EnvironmentTask, TaskStatus
    await require_student_access(current_user, student_id, db)
    query = select(EnvironmentTask).where(EnvironmentTask.student_id == student_id)
    if status:
        try: query = query.where(EnvironmentTask.status == TaskStatus(status))
        except ValueError: raise HTTPException(400, '任务状态无效')
    if task_id: query = query.where(EnvironmentTask.id == task_id)
    try:
        from datetime import timezone
        for raw, lower in [(date_from, True), (date_to, False)]:
            if not raw: continue
            boundary=datetime.fromisoformat(raw)
            if boundary.tzinfo: boundary=boundary.astimezone(timezone.utc).replace(tzinfo=None)
            # SQLite CURRENT_TIMESTAMP omits fractional seconds; comparing its
            # text with bound '.000000' datetimes incorrectly drops equal rows.
            column=EnvironmentTask.created_at
            if db.bind.dialect.name == 'sqlite':
                column=func.julianday(column)
                boundary=func.julianday(boundary)
            query=query.where(column >= boundary if lower else column <= boundary)
    except ValueError: raise HTTPException(400, '时间格式无效')
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    tasks = (await db.execute(query.order_by(EnvironmentTask.created_at.desc(), EnvironmentTask.id).offset((page-1)*page_size).limit(page_size))).scalars().all()
    from app.services.production_data import setting
    items=[]
    for task in tasks:
        chain=await setting(db, 'environment_retry:' + task.id, {})
        items.append({'id':task.id,'status':task.status.value,'score_id':task.score_id,'lab_id':task.lab_id,
          'check_id':task.check_id,'error_message':task.error_message,'created_at':task.created_at,
          'completed_at':task.completed_at,'parent_task_id':chain.get('parent_task_id'), 'root_task_id':chain.get('root_task_id',task.id)})
    return {'total':total,'items':items,'page':page,'page_size':page_size}


@router.post('/tasks/{task_id}/retry', response_model=EnvironmentTaskResponse)
async def retry_environment_task(task_id: str, background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.workflow import EnvironmentTask, TaskStatus
    task=await db.get(EnvironmentTask, task_id)
    if not task: raise HTTPException(404,'环境检查任务不存在')
    await require_student_access(current_user, task.student_id, db)
    if task.status != TaskStatus.FAILED: raise HTTPException(409,'仅可重新提交失败任务')
    try:
        new=await EnvironmentCheckService(db).create_task(task.student_id,task.lab_id,task.image_data,task.score_id,current_user.id,parent_task_id=task.id)
        if not settings.RELEASE_MODE: background_tasks.add_task(process_environment_task,new.id)
        return new
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc


@router.post("/tasks", response_model=EnvironmentTaskResponse)
async def create_environment_task(
    request: EnvironmentCheckRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (["student", "teacher", "admin"] if settings.RELEASE_MODE else ["teacher", "admin"]):
        raise HTTPException(status_code=403, detail="仅教师和管理员可执行环境检查")
    await require_student_access(current_user, request.student_id, db)
    try:
        task = await EnvironmentCheckService(db).create_task(
            request.student_id,
            request.lab_id,
            request.image_base64,
            request.score_id,
            current_user.id,
        )
        if not settings.RELEASE_MODE:
            background_tasks.add_task(process_environment_task, task.id)
        return task
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=EnvironmentTaskResponse)
async def get_environment_task(
    task_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (["student", "teacher", "admin"] if settings.RELEASE_MODE else ["teacher", "admin"]):
        raise HTTPException(status_code=403, detail="仅教师和管理员可访问")
    task = await EnvironmentCheckService(db).get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="环境检查任务不存在")
    await require_student_access(current_user, task.student_id, db)
    return task


@router.get("/labs", response_model=List[LabResponse])
async def get_labs(
    db: AsyncSession = Depends(get_db),
):
    """获取所有实训室"""
    result = await db.execute(select(Lab))
    labs = result.scalars().all()

    return [
        LabResponse(
            id=lab.id,
            name=lab.name,
            building=lab.building,
            floor=lab.floor,
            capacity=lab.capacity,
            equipment=lab.equipment or [],
            reference_image_url=lab.reference_image_url,
            status=lab.status.value,
            current_students=lab.current_students or 0,
        )
        for lab in labs
    ]


@router.get("/labs/{lab_id}", response_model=LabResponse)
async def get_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取实训室详情"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()

    if not lab:
        raise HTTPException(status_code=404, detail="实训室不存在")

    return LabResponse(
        id=lab.id,
        name=lab.name,
        building=lab.building,
        floor=lab.floor,
        capacity=lab.capacity,
        equipment=lab.equipment or [],
        reference_image_url=lab.reference_image_url,
        status=lab.status.value,
        current_students=lab.current_students or 0,
    )


@router.post("/check", response_model=EnvironmentCheckResponse)
async def check_environment(
    request: EnvironmentCheckRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传照片进行环境检查"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="仅教师和管理员可执行环境检查")

    await require_student_access(current_user, request.student_id, db)

    service = EnvironmentCheckService(db)

    try:
        return await service.check_environment(
            student_id=request.student_id,
            lab_id=request.lab_id,
            image_base64=request.image_base64,
            score_id=request.score_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history/{student_id}", response_model=List[EnvironmentCheckResponse])
async def get_student_check_history(
    student_id: str,
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学生查看本人结果，教师/管理员查看授权范围结果。"""
    await require_student_access(current_user, student_id, db)

    service = EnvironmentCheckService(db)
    return await service.get_student_history(student_id, limit)


@router.get("/checks/{check_id}", response_model=EnvironmentCheckResponse)
async def get_check(
    check_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    check = (await db.execute(select(EnvironmentCheck).where(EnvironmentCheck.id == check_id))).scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="环境检查记录不存在")
    await require_student_access(current_user, check.student_id, db)
    return await EnvironmentCheckService(db).get_check(check_id)


@router.post("/checks/{check_id}/review", response_model=EnvironmentCheckResponse)
async def review_check(
    check_id: str,
    data: EnvironmentReviewRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="仅教师和管理员可复核")
    check = (await db.execute(select(EnvironmentCheck).where(EnvironmentCheck.id == check_id))).scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="环境检查记录不存在")
    await require_student_access(current_user, check.student_id, db)
    try:
        return await EnvironmentCheckService(db).review_check(check_id, current_user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/checks/{check_id}/review-history')
async def check_review_history(check_id:str,current_user:UserResponse=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    from app.models.operations import AuditLog
    from app.models.user import User
    check=await db.get(EnvironmentCheck,check_id)
    if not check:raise HTTPException(404,'环境检查不存在')
    await require_student_access(current_user,check.student_id,db)
    rows=(await db.execute(select(AuditLog).where(AuditLog.object_type=='environment',AuditLog.object_id==check_id,AuditLog.action=='environment_review').order_by(AuditLog.created_at,AuditLog.id))).scalars().all()
    result=[]
    for x in rows:
        actor=await db.get(User,x.actor_id) if x.actor_id else None
        result.append({'id':x.id,'actor_id':x.actor_id,'actor_name':actor.name if actor else x.actor_name,'created_at':x.created_at,'before':x.before,'after':x.after,'result':x.result})
    return result
