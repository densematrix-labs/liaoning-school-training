"""
Admin API tests
"""
import pytest


@pytest.mark.asyncio
async def test_list_abilities(client, auth_headers):
    """Test list abilities endpoint"""
    response = await client.get("/api/v1/admin/abilities", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_ability(client, auth_headers):
    """Test create major ability"""
    response = await client.post(
        "/api/v1/admin/abilities",
        headers=auth_headers,
        json={
            "name": "测试能力",
            "description": "测试能力描述",
            "weight": 0.2,
            "graduation_threshold": 0.6
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试能力"
    assert data["weight"] == 0.2


@pytest.mark.asyncio
async def test_update_ability(client, auth_headers, test_db):
    """Test update major ability"""
    from app.models.ability import MajorAbility
    
    # Create ability first
    async with test_db() as session:
        ability = MajorAbility(
            id="update-test-ability",
            name="Original Name",
            weight=0.25
        )
        session.add(ability)
        await session.commit()
    
    # Update it
    response = await client.put(
        "/api/v1/admin/abilities/update-test-ability",
        headers=auth_headers,
        json={
            "name": "Updated Name",
            "weight": 0.3
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["weight"] == 0.3


@pytest.mark.asyncio
async def test_delete_ability(client, auth_headers, test_db):
    """Test delete major ability"""
    from app.models.ability import MajorAbility
    
    # Create ability first
    async with test_db() as session:
        ability = MajorAbility(
            id="delete-test-ability",
            name="To Delete",
            weight=0.25
        )
        session.add(ability)
        await session.commit()
    
    # Delete it
    response = await client.delete(
        "/api/v1/admin/abilities/delete-test-ability",
        headers=auth_headers
    )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_labs(client, auth_headers):
    """Test list labs endpoint"""
    response = await client.get("/api/v1/admin/labs", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_lab(client, auth_headers):
    """Test create lab"""
    response = await client.post(
        "/api/v1/admin/labs",
        headers=auth_headers,
        json={
            "name": "测试实训室",
            "building": "测试楼",
            "capacity": 10
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试实训室"
    assert data["capacity"] == 10


@pytest.mark.asyncio
async def test_admin_unauthorized(client):
    """Test admin endpoint without auth"""
    response = await client.get("/api/v1/admin/abilities")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_forbidden(client, student_headers):
    """Test admin endpoint with student role"""
    response = await client.get("/api/v1/admin/abilities", headers=student_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_sync_trigger(client, auth_headers):
    """Test manual sync trigger"""
    response = await client.post("/api/v1/admin/sync", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
