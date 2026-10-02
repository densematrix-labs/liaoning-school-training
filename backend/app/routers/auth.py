from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import AuthService
from app.schemas.auth import Token, LoginRequest, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    auth_service = AuthService(db)
    token_data = auth_service.decode_token(token)
    return await auth_service.get_current_user(token_data.user_id, token_data.version)


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    auth_service = AuthService(db)
    return await auth_service.login(request.username, request.password, http_request.client.host if http_request.client else None)


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """用户登录 (表单)"""
    auth_service = AuthService(db)
    return await auth_service.login(form_data.username, form_data.password)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
):
    """获取当前用户信息"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """刷新 Token"""
    auth_service = AuthService(db)
    token_data = auth_service.decode_token(token, token_type="refresh")
    user = await auth_service.get_current_user(token_data.user_id, token_data.version)
    import hashlib
    from app.services.production_data import setting, put_setting
    used_key = "refresh:" + hashlib.sha256(token.encode()).hexdigest()
    if await setting(db, used_key):
        raise HTTPException(401, "刷新凭据已使用")
    await put_setting(db, used_key, {"used": True})
    await db.commit()
    
    # Create new tokens
    new_access = auth_service.create_access_token({
        "sub": token_data.user_id,
        "role": user.role,
        "ver": token_data.version,
    })
    new_refresh = auth_service.create_refresh_token({
        "sub": token_data.user_id,
        "role": user.role,
        "ver": token_data.version,
    })
    
    return Token(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.account_security import revoke
    await revoke(db, current_user.id)
    await db.commit()
    return {"message":"已撤销该账号的现有会话"}
