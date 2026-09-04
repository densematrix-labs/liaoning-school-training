"""
管理后台 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, delete, func
from datetime import datetime
from typing import List, Optional
import uuid
import csv
import io

from app.database import get_db
from app.models.user import User, UserRole
from app.models.ability import MajorAbility, SubAbility
from app.models.lab import Lab
from app.models.training import TrainingProject
from app.models.training import Score
from app.models.student import Student, Class
from app.models.report import DiagnosticReport
from app.models.workflow import MockSyncException, MockSyncTask, TaskStatus
from app.adapters.controllers.auth import get_current_admin
from app.services.recalculation import RecalculationService
from app.schemas.admin import (
    ProjectRuleUpdate,
    RecalculateRequest,
    SyncExceptionResponse,
    SyncTaskResponse,
    TeacherAssignmentRequest,
)
from app.schemas.ability import (
    MajorAbilityCreate,
    MajorAbilityUpdate,
    MajorAbilityResponse,
    SubAbilityCreate,
    SubAbilityUpdate,
    SubAbilityResponse,
    AbilityMappingResponse,
)
from app.schemas.lab import LabCreate, LabUpdate, LabResponse

router = APIRouter()


@router.get("/overview")
async def get_admin_overview(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """管理员首页所需的全校数据概览。"""
    entities = {
        "students": Student,
        "classes": Class,
        "scores": Score,
        "abilities": MajorAbility,
        "labs": Lab,
        "reports": DiagnosticReport,
    }
    counts = {}
    for key, model in entities.items():
        result = await db.execute(select(func.count()).select_from(model))
        counts[key] = result.scalar() or 0

    latest_score = await db.execute(select(func.max(Score.calculated_at)))
    return {
        **counts,
        "database": "SQLite 演示库",
        "sync_status": "正常",
        "last_data_at": latest_score.scalar(),
    }


# ============ 权限范围管理 ============

@router.get("/access-control")
async def get_access_control(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """查看角色权限说明和教师班级授权。"""
    teachers = list((await db.execute(
        select(User).where(User.role == UserRole.TEACHER).order_by(User.name)
    )).scalars().all())
    classes = list((await db.execute(
        select(Class).options(selectinload(Class.teacher)).order_by(Class.year.desc(), Class.name)
    )).scalars().all())
    return {
        "role_scopes": [
            {"role": "student", "label": "学生", "scope": "仅本人成绩、能力和诊断报告"},
            {"role": "teacher", "label": "教师", "scope": "仅已授权班级，可复核环境检查"},
            {"role": "admin", "label": "管理员", "scope": "全校数据与业务规则管理"},
        ],
        "teachers": [{"id": item.id, "name": item.name, "username": item.username} for item in teachers],
        "classes": [
            {
                "id": item.id,
                "name": item.name,
                "year": item.year,
                "teacher_id": item.teacher_id,
                "teacher_name": item.teacher.name if item.teacher else None,
            }
            for item in classes
        ],
    }


@router.put("/classes/{class_id}/teacher")
async def assign_class_teacher(
    class_id: str,
    data: TeacherAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    class_ = (await db.execute(select(Class).where(Class.id == class_id))).scalar_one_or_none()
    if not class_:
        raise HTTPException(status_code=404, detail="班级不存在")
    if data.teacher_id:
        teacher = (await db.execute(
            select(User).where(User.id == data.teacher_id, User.role == UserRole.TEACHER)
        )).scalar_one_or_none()
        if not teacher:
            raise HTTPException(status_code=400, detail="指定账号不是教师")
    class_.teacher_id = data.teacher_id
    await db.commit()
    return {"message": "班级数据范围已更新", "class_id": class_.id, "teacher_id": class_.teacher_id}


# ============ 能力管理 ============

@router.get("/abilities", response_model=List[MajorAbilityResponse])
async def list_major_abilities(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取所有大类能力"""
    result = await db.execute(
        select(MajorAbility).order_by(MajorAbility.display_order)
    )
    abilities = result.scalars().all()
    
    response = []
    for ability in abilities:
        # 获取子能力
        sub_result = await db.execute(
            select(SubAbility).where(SubAbility.major_ability_id == ability.id)
        )
        sub_abilities = sub_result.scalars().all()
        
        response.append(MajorAbilityResponse(
            id=ability.id,
            name=ability.name,
            description=ability.description,
            weight=ability.weight,
            graduation_threshold=ability.graduation_threshold,
            icon=ability.icon,
            display_order=ability.display_order,
            sub_abilities=[
                SubAbilityResponse(
                    id=sa.id,
                    major_ability_id=sa.major_ability_id,
                    name=sa.name,
                    description=sa.description,
                    weight=sa.weight
                )
                for sa in sub_abilities
            ]
        ))
    
    return response


@router.post("/abilities", response_model=MajorAbilityResponse)
async def create_major_ability(
    data: MajorAbilityCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """创建大类能力"""
    ability = MajorAbility(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        weight=data.weight,
        graduation_threshold=data.graduation_threshold,
        icon=data.icon,
        display_order=data.display_order or 0
    )
    db.add(ability)
    await db.commit()
    await db.refresh(ability)
    
    return MajorAbilityResponse(
        id=ability.id,
        name=ability.name,
        description=ability.description,
        weight=ability.weight,
        graduation_threshold=ability.graduation_threshold,
        icon=ability.icon,
        display_order=ability.display_order,
        sub_abilities=[]
    )


@router.put("/abilities/{ability_id}", response_model=MajorAbilityResponse)
async def update_major_ability(
    ability_id: str,
    data: MajorAbilityUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """更新大类能力"""
    result = await db.execute(
        select(MajorAbility).where(MajorAbility.id == ability_id)
    )
    ability = result.scalar_one_or_none()
    
    if not ability:
        raise HTTPException(status_code=404, detail="能力不存在")
    
    if data.name is not None:
        ability.name = data.name
    if data.description is not None:
        ability.description = data.description
    if data.weight is not None:
        ability.weight = data.weight
    if data.graduation_threshold is not None:
        ability.graduation_threshold = data.graduation_threshold
    if data.icon is not None:
        ability.icon = data.icon
    if data.display_order is not None:
        ability.display_order = data.display_order
    
    await db.commit()
    await db.refresh(ability)
    
    # 获取子能力
    sub_result = await db.execute(
        select(SubAbility).where(SubAbility.major_ability_id == ability.id)
    )
    sub_abilities = sub_result.scalars().all()
    
    return MajorAbilityResponse(
        id=ability.id,
        name=ability.name,
        description=ability.description,
        weight=ability.weight,
        graduation_threshold=ability.graduation_threshold,
        icon=ability.icon,
        display_order=ability.display_order,
        sub_abilities=[
            SubAbilityResponse(
                id=sa.id,
                major_ability_id=sa.major_ability_id,
                name=sa.name,
                description=sa.description,
                weight=sa.weight
            )
            for sa in sub_abilities
        ]
    )


@router.delete("/abilities/{ability_id}")
async def delete_major_ability(
    ability_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """删除大类能力"""
    # 先删除子能力
    await db.execute(
        delete(SubAbility).where(SubAbility.major_ability_id == ability_id)
    )
    
    # 删除大类能力
    await db.execute(
        delete(MajorAbility).where(MajorAbility.id == ability_id)
    )
    
    await db.commit()
    return {"message": "删除成功"}


# ============ 子能力管理 ============

@router.post("/abilities/{ability_id}/sub-abilities", response_model=SubAbilityResponse)
async def create_sub_ability(
    ability_id: str,
    data: SubAbilityCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """创建子能力"""
    # 验证大类能力存在
    result = await db.execute(
        select(MajorAbility).where(MajorAbility.id == ability_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="大类能力不存在")
    
    sub_ability = SubAbility(
        id=str(uuid.uuid4()),
        major_ability_id=ability_id,
        name=data.name,
        description=data.description,
        weight=data.weight
    )
    db.add(sub_ability)
    await db.commit()
    await db.refresh(sub_ability)
    
    return SubAbilityResponse(
        id=sub_ability.id,
        major_ability_id=sub_ability.major_ability_id,
        name=sub_ability.name,
        description=sub_ability.description,
        weight=sub_ability.weight
    )


@router.put("/sub-abilities/{sub_ability_id}", response_model=SubAbilityResponse)
async def update_sub_ability(
    sub_ability_id: str,
    data: SubAbilityUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """更新子能力"""
    result = await db.execute(
        select(SubAbility).where(SubAbility.id == sub_ability_id)
    )
    sub_ability = result.scalar_one_or_none()
    
    if not sub_ability:
        raise HTTPException(status_code=404, detail="子能力不存在")
    
    if data.name is not None:
        sub_ability.name = data.name
    if data.description is not None:
        sub_ability.description = data.description
    if data.weight is not None:
        sub_ability.weight = data.weight
    
    await db.commit()
    await db.refresh(sub_ability)
    
    return SubAbilityResponse(
        id=sub_ability.id,
        major_ability_id=sub_ability.major_ability_id,
        name=sub_ability.name,
        description=sub_ability.description,
        weight=sub_ability.weight
    )


@router.delete("/sub-abilities/{sub_ability_id}")
async def delete_sub_ability(
    sub_ability_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """删除子能力"""
    await db.execute(
        delete(SubAbility).where(SubAbility.id == sub_ability_id)
    )
    await db.commit()
    return {"message": "删除成功"}


# ============ 实训室管理 ============

@router.get("/labs", response_model=List[LabResponse])
async def list_labs(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
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
            current_students=lab.current_students
        )
        for lab in labs
    ]


@router.post("/labs", response_model=LabResponse)
async def create_lab(
    data: LabCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """创建实训室"""
    lab = Lab(
        id=str(uuid.uuid4()),
        name=data.name,
        building=data.building,
        floor=data.floor,
        capacity=data.capacity,
        equipment=data.equipment,
        reference_image_url=data.reference_image_url
    )
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    
    return LabResponse(
        id=lab.id,
        name=lab.name,
        building=lab.building,
        floor=lab.floor,
        capacity=lab.capacity,
        equipment=lab.equipment or [],
        reference_image_url=lab.reference_image_url,
        status=lab.status.value,
        current_students=lab.current_students
    )


@router.put("/labs/{lab_id}", response_model=LabResponse)
async def update_lab(
    lab_id: str,
    data: LabUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """更新实训室"""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail="实训室不存在")
    
    if data.name is not None:
        lab.name = data.name
    if data.building is not None:
        lab.building = data.building
    if data.floor is not None:
        lab.floor = data.floor
    if data.capacity is not None:
        lab.capacity = data.capacity
    if data.equipment is not None:
        lab.equipment = data.equipment
    if data.reference_image_url is not None:
        lab.reference_image_url = data.reference_image_url
    
    await db.commit()
    await db.refresh(lab)
    
    return LabResponse(
        id=lab.id,
        name=lab.name,
        building=lab.building,
        floor=lab.floor,
        capacity=lab.capacity,
        equipment=lab.equipment or [],
        reference_image_url=lab.reference_image_url,
        status=lab.status.value,
        current_students=lab.current_students
    )


@router.delete("/labs/{lab_id}")
async def delete_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """删除实训室"""
    await db.execute(delete(Lab).where(Lab.id == lab_id))
    await db.commit()
    return {"message": "删除成功"}


# ============ 能力映射管理 ============

@router.get("/projects")
async def list_training_projects(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    projects = list((await db.execute(select(TrainingProject).order_by(TrainingProject.name))).scalars().all())
    response = []
    for project in projects:
        sample_scores = list((await db.execute(
            select(Score)
            .where(Score.project_id == project.id)
            .order_by(Score.calculated_at.desc())
            .limit(8)
        )).scalars().all())
        response.append({
            "id": project.id,
            "name": project.name,
            "max_score": project.max_score,
            "steps": project.steps or [],
            "scoring_rules": project.scoring_rules or {},
            "ability_mapping": project.ability_mapping or {},
            "sample_scores": [
                {"id": item.id, "student_id": item.student_id, "total_score": item.total_score, "calculated_at": item.calculated_at}
                for item in sample_scores
            ],
        })
    return response


@router.put("/projects/{project_id}/configuration")
async def update_project_configuration(
    project_id: str,
    data: ProjectRuleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    project = (await db.execute(select(TrainingProject).where(TrainingProject.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="实训项目不存在")
    if not data.steps:
        raise HTTPException(status_code=400, detail="至少保留一个操作步骤")

    step_ids = {str(item.get("id")) for item in data.steps if item.get("id")}
    if len(step_ids) != len(data.steps):
        raise HTTPException(status_code=400, detail="步骤 ID 不能为空或重复")
    for step in data.steps:
        if float(step.get("score", 0)) <= 0:
            raise HTTPException(status_code=400, detail="步骤满分必须大于 0")
        if float(step.get("failed_score", 0)) < 0 or float(step.get("failed_score", 0)) > float(step.get("score", 0)):
            raise HTTPException(status_code=400, detail="未通过得分必须在 0 和步骤满分之间")
    if set(data.ability_mapping) - step_ids:
        raise HTTPException(status_code=400, detail="能力映射包含不存在的步骤")

    project.steps = data.steps
    project.ability_mapping = data.ability_mapping
    project.max_score = round(sum(float(item.get("score", 0)) for item in data.steps), 2)
    project.scoring_rules = {
        **(project.scoring_rules or {}),
        "mode": "passed_or_failed",
        "version": int((project.scoring_rules or {}).get("version", 0)) + 1,
    }
    await db.commit()
    return {
        "message": "评分规则与能力映射已保存",
        "project_id": project.id,
        "max_score": project.max_score,
        "rule_version": project.scoring_rules["version"],
    }


@router.post("/projects/{project_id}/recalculate")
async def recalculate_project_scores(
    project_id: str,
    data: RecalculateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        return await RecalculationService(db).recalculate_project(project_id, data.score_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/mappings", response_model=List[AbilityMappingResponse])
async def list_ability_mappings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取能力映射列表"""
    # 获取所有实训项目
    result = await db.execute(select(TrainingProject))
    projects = result.scalars().all()
    
    mappings = []
    for project in projects:
        if not project.ability_mapping:
            continue
        
        mappings.append(AbilityMappingResponse(
            project_id=project.id,
            project_name=project.name,
            step_mappings=project.ability_mapping
        ))
    
    return mappings


@router.put("/mappings/{project_id}")
async def update_ability_mapping(
    project_id: str,
    mapping: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """更新能力映射"""
    result = await db.execute(
        select(TrainingProject).where(TrainingProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="实训项目不存在")
    
    project.ability_mapping = mapping
    await db.commit()
    
    return {"message": "更新成功"}


# ============ 数据同步 ============

async def _sync_task_response(db: AsyncSession, task: MockSyncTask) -> SyncTaskResponse:
    exceptions = list((await db.execute(
        select(MockSyncException).where(MockSyncException.task_id == task.id).order_by(MockSyncException.row_number)
    )).scalars().all())
    return SyncTaskResponse(
        id=task.id,
        status=task.status.value,
        read_count=task.read_count,
        success_count=task.success_count,
        skipped_count=task.skipped_count,
        error_count=task.error_count,
        started_at=task.started_at,
        completed_at=task.completed_at,
        exceptions=[
            SyncExceptionResponse(
                id=item.id,
                row_number=item.row_number,
                source_record_id=item.source_record_id,
                reason=item.reason,
                raw_data=item.raw_data,
            )
            for item in exceptions
        ],
    )


@router.get("/sync/history", response_model=List[SyncTaskResponse])
async def list_sync_history(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    tasks = list((await db.execute(
        select(MockSyncTask).order_by(MockSyncTask.started_at.desc()).limit(20)
    )).scalars().all())
    return [await _sync_task_response(db, task) for task in tasks]


@router.get("/sync/{task_id}/exceptions.csv")
async def export_sync_exceptions(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = list((await db.execute(
        select(MockSyncException).where(MockSyncException.task_id == task_id).order_by(MockSyncException.row_number)
    )).scalars().all())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["行号", "源记录标识", "失败原因"])
    for item in rows:
        writer.writerow([item.row_number, item.source_record_id or "", item.reason])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="sync-{task_id}-exceptions.csv"'},
    )

@router.post("/sync")
async def trigger_sync(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """运行可重复的 Mock 同步演示，不连接校方数据库。"""
    previous_count = (await db.execute(select(func.count()).select_from(MockSyncTask))).scalar() or 0
    task = MockSyncTask(
        id=str(uuid.uuid4()),
        status=TaskStatus.COMPLETED,
        read_count=6,
        success_count=3 if previous_count == 0 else 0,
        skipped_count=2 if previous_count == 0 else 5,
        error_count=1,
        created_by=admin.id,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(task)
    await db.flush()
    db.add(MockSyncException(
        id=str(uuid.uuid4()),
        task_id=task.id,
        row_number=6,
        source_record_id="DEMO-INVALID-001",
        reason="步骤标识无法匹配演示项目",
        raw_data={"student_no": "2023010101", "step_id": "UNKNOWN"},
    ))
    await db.commit()
    return await _sync_task_response(db, task)
