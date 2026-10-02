from datetime import datetime, timedelta
import uuid
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User, UserRole
from app.models.student import Student, Class, TeacherClassAssignment
from app.schemas.auth import Token, TokenData, UserResponse

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def decode_token(token: str, token_type: str = "access") -> TokenData:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            role: str = payload.get("role")
            if user_id is None or payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的认证凭据",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return TokenData(user_id=user_id, role=role, version=payload.get("ver", 0))
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user or not self.verify_password(password, user.password_hash):
            return None
        return user
    
    async def login(self, username: str, password: str, ip: str | None = None) -> Token:
        from app.services.account_security import require_not_locked, login_attempt, validate_account
        await require_not_locked(self.db, username)
        user = await self.authenticate_user(username, password)
        if not user:
            await login_attempt(self.db, username, False, ip=ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        state = await validate_account(self.db, user)
        await login_attempt(self.db, username, True, user=user, ip=ip)
        token_data = {"sub": user.id, "role": user.role.value, "ver": state.get("version",0)}
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return Token(access_token=access_token, refresh_token=refresh_token)
    
    async def get_current_user(self, user_id: str, version: int | None = None) -> UserResponse:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        from app.services.account_security import validate_account
        await validate_account(self.db, user, version)
        
        response = UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            role=user.role.value,
            created_at=user.created_at
        )
        
        # Add student-specific info
        if user.role == UserRole.STUDENT:
            student_result = await self.db.execute(
                select(Student).where(Student.user_id == user.id)
            )
            student = student_result.scalar_one_or_none()
            if student:
                response.student_id = student.id
                response.student_no = student.student_no
                
                # Get class name
                class_result = await self.db.execute(
                    select(Class).where(Class.id == student.class_id)
                )
                class_obj = class_result.scalar_one_or_none()
                if class_obj:
                    response.class_name = class_obj.name
                    
                    # Get major name
                    from app.models.student import Major
                    major_result = await self.db.execute(
                        select(Major).where(Major.id == student.major_id)
                    )
                    major = major_result.scalar_one_or_none()
                    if major:
                        response.major_name = major.name
        
        # Add teacher-specific info
        elif user.role == UserRole.TEACHER:
            classes_result = await self.db.execute(
                select(Class)
                .outerjoin(TeacherClassAssignment, TeacherClassAssignment.class_id == Class.id)
                .where(or_(
                    TeacherClassAssignment.teacher_id == user.id,
                    Class.teacher_id == user.id,
                ))
                .distinct()
                .order_by(Class.year.desc(), Class.name)
            )
            classes = classes_result.scalars().all()
            response.classes = [{"id": c.id, "name": c.name} for c in classes]
        
        return response
