"""
管理后台 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
import uuid

from app.database import get_db
from app.models.user import User
from app.models.ability import MajorAbility, SubAbility
from app.models.lab import Lab
from app.models.training import TrainingProject
from app.adapters.controllers.auth import get_current_admin
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

@router.post("/sync")
async def trigger_sync(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """手动触发数据同步"""
    # 这里是 Demo，直接返回成功
    # 实际项目中会从校方 MySQL 同步数据
    return {
        "message": "同步完成",
        "synced_records": 0,
        "timestamp": "2026-03-04T00:00:00"
    }
