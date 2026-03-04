import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ability import MajorAbility, SubAbility


@pytest.mark.asyncio
async def test_get_ability_schema_empty(client: AsyncClient):
    """Test get ability schema when empty"""
    response = await client.get("/api/v1/abilities/schema")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_ability_schema(client: AsyncClient, db_session: AsyncSession):
    """Test get ability schema with data"""
    # Create test ability
    ma = MajorAbility(
        id="test-ma-001",
        name="测试能力",
        description="测试描述",
        weight=0.25,
        graduation_threshold=0.6,
        display_order=0,
    )
    db_session.add(ma)
    
    sa = SubAbility(
        id="test-sa-001",
        major_ability_id="test-ma-001",
        name="测试子能力",
        description="测试子能力描述",
        weight=0.5,
    )
    db_session.add(sa)
    await db_session.commit()
    
    response = await client.get("/api/v1/abilities/schema")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "测试能力"
    assert len(data[0]["sub_abilities"]) == 1


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """Test get profile without auth"""
    response = await client.get("/api/v1/abilities/profile")
    assert response.status_code == 401
