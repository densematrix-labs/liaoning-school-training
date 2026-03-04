"""
Authentication API tests
"""
import pytest


@pytest.mark.asyncio
async def test_login_success(client, test_db):
    """Test successful login"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with test_db() as session:
        user = User(
            id="login-test-user",
            username="logintest",
            password_hash=pwd_context.hash("password123"),
            name="Login Test",
            role=UserRole.STUDENT
        )
        session.add(user)
        await session.commit()
    
    response = await client.post("/api/v1/auth/login", json={
        "username": "logintest",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_db):
    """Test login with wrong password"""
    from passlib.context import CryptContext
    from app.models.user import User, UserRole
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async with test_db() as session:
        user = User(
            id="wrong-pass-user",
            username="wrongpass",
            password_hash=pwd_context.hash("correct"),
            name="Test",
            role=UserRole.STUDENT
        )
        session.add(user)
        await session.commit()
    
    response = await client.post("/api/v1/auth/login", json={
        "username": "wrongpass",
        "password": "wrong"
    })
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_user_not_found(client, test_db):
    """Test login with non-existent user"""
    response = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "password"
    })
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client, auth_headers):
    """Test get current user endpoint"""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_current_user_no_token(client):
    """Test get current user without token"""
    response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client):
    """Test get current user with invalid token"""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401
