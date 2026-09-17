from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    actor_id: str | None,
    actor_name: str | None,
    action: str,
    object_type: str,
    object_id: str | None = None,
    result: str = "success",
    reason: str | None = None,
    before: Any = None,
    after: Any = None,
) -> AuditLog:
    item = AuditLog(
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        object_type=object_type,
        object_id=object_id,
        result=result,
        reason=reason,
        before=before,
        after=after,
    )
    db.add(item)
    await db.flush()
    return item
