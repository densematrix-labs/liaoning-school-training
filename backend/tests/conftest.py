"""
Pytest configuration and fixtures
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create test database engine and session"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestSessionLocal
    
    app.dependency_overrides.clear()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    """Create async test client"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client, test_db):
    """Get authenticated headers for tests"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with test_db() as session:
        # Create test user
        user = User(
            id="test-user-1",
            username="testuser",
            password_hash=pwd_context.hash("testpass"),
            name="Test User",
            role=UserRole.ADMIN
        )
        session.add(user)
        await session.commit()
    
    # Login to get token
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def student_headers(client, test_db):
    """Get student authenticated headers"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole
    from app.models.student import Student, Class, Major
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with test_db() as session:
        # Create major
        major = Major(
            id="test-major",
            code="TEST001",
            name="Test Major"
        )
        session.add(major)
        
        # Create class
        cls = Class(
            id="test-class",
            name="Test Class",
            major_id="test-major",
            year=2023
        )
        session.add(cls)
        
        # Create user
        user = User(
            id="test-student-user",
            username="student001",
            password_hash=pwd_context.hash("testpass"),
            name="Test Student",
            role=UserRole.STUDENT
        )
        session.add(user)
        
        # Create student
        student = Student(
            id="test-student",
            user_id="test-student-user",
            student_no="2023010101",
            name="Test Student",
            major_id="test-major",
            class_id="test-class",
            enrollment_year=2023
        )
        session.add(student)
        await session.commit()
    
    # Login
    response = await client.post("/api/v1/auth/login", json={
        "username": "student001",
        "password": "testpass"
    })
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
