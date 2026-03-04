from fastapi import APIRouter, Depends, HTTPException, status
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
    return await auth_service.get_current_user(token_data.user_id)


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    auth_service = AuthService(db)
    return await auth_service.login(request.username, request.password)


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
    token_data = auth_service.decode_token(token)
    
    # Create new tokens
    new_access = auth_service.create_access_token({
        "sub": token_data.user_id,
        "role": token_data.role,
    })
    new_refresh = auth_service.create_refresh_token({
        "sub": token_data.user_id,
        "role": token_data.role,
    })
    
    return Token(access_token=new_access, refresh_token=new_refresh)
