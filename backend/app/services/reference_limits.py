from fastapi import HTTPException
from sqlalchemy import select, update, func
from app.models.lab import Lab
from app.models.operations import ReferenceImage

async def reserve_reference_slot(db, lab_id):
    # Lock the parent before counting so simultaneous uploads cannot exceed the cap.
    result = await db.execute(update(Lab).where(Lab.id == lab_id).values(name=Lab.name))
    if not result.rowcount:
        raise HTTPException(404, '实训室不存在')
    count = (await db.execute(select(func.count()).select_from(ReferenceImage).where(ReferenceImage.lab_id == lab_id))).scalar_one()
    if count >= 2:
        raise HTTPException(400, '每间实训室最多保存两张标准状态参考图片')
