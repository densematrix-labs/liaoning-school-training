"""OIDC authorization-code + PKCE; identities must be explicitly bound locally."""
import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from jose import jwt
from sqlalchemy import select, delete

from app.database import get_db
from app.models.operations import SystemSetting
from app.models.user import User
from app.services.production_data import setting, put_setting
from app.services.account_security import validate_account
from app.services.auth import AuthService
from app.services.audit import record_audit

router = APIRouter(prefix="/api/v1/sso", tags=["校园统一认证"])


def config():
    result = {key: os.getenv("OIDC_" + key.upper(), "") for key in ("issuer","client_id","client_secret","redirect_uri")}
    if not all(result.values()):
        raise HTTPException(503, "校园统一认证尚未配置；需校方提供 OIDC 接入参数")
    if not all(result[key].startswith("https://") for key in ("issuer","redirect_uri")):
        raise HTTPException(503, "统一认证要求 HTTPS issuer 和回调地址")
    return result


async def discovery(cfg):
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        response = await client.get(cfg["issuer"].rstrip("/") + "/.well-known/openid-configuration")
        response.raise_for_status()
        metadata = response.json()
    if metadata.get("issuer") != cfg["issuer"]:
        raise HTTPException(502, "认证提供方 issuer 不匹配")
    for key in ("authorization_endpoint","token_endpoint","jwks_uri"):
        if not str(metadata.get(key, "")).startswith("https://"):
            raise HTTPException(502, "认证提供方端点不安全")
    return metadata


@router.get("/status")
async def status():
    return {"enabled": all(os.getenv("OIDC_"+key) for key in ("ISSUER","CLIENT_ID","CLIENT_SECRET","REDIRECT_URI")), "protocol":"OIDC"}


@router.get("/login")
async def start(db=Depends(get_db)):
    cfg = config()
    metadata = await discovery(cfg)
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    await put_setting(db, "oidc:"+state, {"nonce":nonce,"verifier":verifier,"expires":(datetime.utcnow()+timedelta(minutes=5)).isoformat()})
    await db.commit()
    params = {"client_id":cfg["client_id"],"redirect_uri":cfg["redirect_uri"],"response_type":"code","scope":"openid",
              "state":state,"nonce":nonce,"code_challenge_method":"S256",
              "code_challenge":base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")}
    response = RedirectResponse(metadata["authorization_endpoint"] + "?" + urlencode(params), status_code=302)
    response.set_cookie("oidc_state", state, max_age=300, httponly=True, secure=True, samesite="lax", path="/api/v1/sso")
    return response


@router.get("/callback")
async def callback(request: Request, code: str, state: str, db=Depends(get_db)):
    if not secrets.compare_digest(request.cookies.get("oidc_state", ""), state):
        raise HTTPException(400, "统一认证状态校验失败")
    saved = await setting(db, "oidc:"+state)
    if not saved or datetime.fromisoformat(saved["expires"]) < datetime.utcnow():
        raise HTTPException(400, "统一认证请求已过期或已使用")
    removed = await db.execute(delete(SystemSetting).where(SystemSetting.key == "oidc:"+state))
    if removed.rowcount != 1:
        raise HTTPException(400, "统一认证请求已使用")
    await db.commit()
    cfg = config()
    metadata = await discovery(cfg)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(metadata["token_endpoint"], data={"grant_type":"authorization_code","code":code,
                "redirect_uri":cfg["redirect_uri"],"client_id":cfg["client_id"],"client_secret":cfg["client_secret"],"code_verifier":saved["verifier"]})
            response.raise_for_status()
            keys = await client.get(metadata["jwks_uri"])
            keys.raise_for_status()
            claims = jwt.decode(response.json()["id_token"], keys.json(), algorithms=["RS256"], audience=cfg["client_id"], issuer=cfg["issuer"],
                                options={"require_exp":True,"require_iat":True,"require_sub":True})
        if claims.get("nonce") != saved["nonce"] or claims.get("azp",cfg["client_id"]) != cfg["client_id"]:
            raise ValueError("nonce/authorized party mismatch")
    except (httpx.HTTPError, ValueError, KeyError, jwt.JWTError) as exc:
        raise HTTPException(401, "统一认证签名或身份校验失败") from exc
    identity_key = "oidc_identity:" + hashlib.sha256(f'{cfg["issuer"]}|{claims["sub"]}'.encode()).hexdigest()
    identity = await setting(db, identity_key)
    user = await db.get(User, identity["user_id"]) if identity else None
    if not user:
        raise HTTPException(403, "该校园身份未绑定本地账号，请联系管理员")
    await validate_account(db, user)
    ticket = secrets.token_urlsafe(32)
    await put_setting(db, "handoff:"+ticket, {"user_id":user.id,"expires":(datetime.utcnow()+timedelta(seconds=60)).isoformat()})
    await record_audit(db, actor_id=user.id, actor_name=user.name, action="sso_login", object_type="session")
    await db.commit()
    response = RedirectResponse("/login?sso=1", status_code=302)
    response.delete_cookie("oidc_state", path="/api/v1/sso")
    response.set_cookie("sso_handoff",ticket,max_age=60,httponly=True,secure=True,samesite="strict",path="/api/v1/sso")
    return response


@router.post("/exchange")
async def exchange(request: Request, db=Depends(get_db)):
    # An HttpOnly same-site cookie binds the one-time handoff to the browser.
    key = "handoff:" + request.cookies.get("sso_handoff", "")
    ticket = await setting(db,key)
    if not ticket or datetime.fromisoformat(ticket["expires"]) < datetime.utcnow():
        raise HTTPException(401,"统一认证登录已过期")
    removed = await db.execute(delete(SystemSetting).where(SystemSetting.key == key))
    if removed.rowcount != 1:
        raise HTTPException(401,"统一认证登录已使用")
    user = await db.get(User,ticket["user_id"])
    if not user:
        raise HTTPException(401,"账号不存在")
    security = await validate_account(db,user)
    data = {"sub":user.id,"role":user.role.value,"ver":security.get("version",0)}
    await db.commit()
    response = JSONResponse({"access_token":AuthService.create_access_token(data),"refresh_token":AuthService.create_refresh_token(data),"token_type":"bearer"})
    response.delete_cookie("sso_handoff",path="/api/v1/sso")
    response.headers["Cache-Control"] = "no-store"
    return response
