"""Persistent account state and revocable sessions, without changing legacy tables."""
import hashlib
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.services.production_data import setting, put_setting
from app.services.audit import record_audit


async def validate_account(db, user, version=None):
    from sqlalchemy import select
    from app.models.operations import SystemSetting
    rows=(await db.execute(select(SystemSetting).where(SystemSetting.key.in_([f"security:{user.id}",f"state:accounts:{user.id}"])))).scalars().all()
    values={row.key:row.value for row in rows}
    state=values.get(f"security:{user.id}",{})
    object_state=values.get(f"state:accounts:{user.id}",{})
    if not state.get("enabled", True) or not object_state.get("enabled", True):
        raise HTTPException(401, "账号已停用")
    if version is not None and version != state.get("version", 0):
        raise HTTPException(401, "会话已失效，请重新登录")
    return state


async def login_attempt(db, username, success, user=None, ip=None):
    key = "login:" + hashlib.sha256(username.lower().encode()).hexdigest()[:48]
    state = await setting(db, key, {})
    now = datetime.utcnow()
    if state.get("locked_until") and datetime.fromisoformat(state["locked_until"]) > now:
        raise HTTPException(429, "登录尝试过多，请稍后重试")
    if success:
        state = {"failures":0}
    else:
        # The counter is a 15-minute window, persisted across service restarts.
        if not state.get("window_start") or now - datetime.fromisoformat(state["window_start"]) > timedelta(minutes=15):
            state = {"failures":0,"window_start":now.isoformat()}
        state["failures"] = state.get("failures",0) + 1
        if state["failures"] >= 5:
            state["locked_until"] = (now + timedelta(minutes=15)).isoformat()
    await put_setting(db, key, state)
    await record_audit(db, actor_id=user.id if user else None, actor_name=username[:50], action="login", object_type="session",
                       result="success" if success else "failed", reason=None if success else "invalid_credentials",
                       after={"ip":ip})
    await db.commit()


async def require_not_locked(db, username):
    key = "login:" + hashlib.sha256(username.lower().encode()).hexdigest()[:48]
    state = await setting(db, key, {})
    if state.get("locked_until") and datetime.fromisoformat(state["locked_until"]) > datetime.utcnow():
        raise HTTPException(429, "登录尝试过多，请稍后重试")


async def revoke(db, user_id, enabled=None):
    state = await setting(db, f"security:{user_id}", {})
    state["version"] = state.get("version",0) + 1
    if enabled is not None:
        state["enabled"] = enabled
    await put_setting(db, f"security:{user_id}", state)
    return state
