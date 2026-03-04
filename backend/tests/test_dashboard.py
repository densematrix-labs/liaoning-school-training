"""
Dashboard API tests
"""
import pytest


@pytest.mark.asyncio
async def test_dashboard_overview(client, test_db):
    """Test dashboard overview endpoint"""
    response = await client.get("/api/v1/dashboard/overview")
    
    assert response.status_code == 200
    data = response.json()
    assert "today_training_count" in data
    assert "pass_rate" in data
    assert "in_training_count" in data
    assert "current_time" in data


@pytest.mark.asyncio
async def test_dashboard_realtime(client, test_db):
    """Test realtime activities endpoint"""
    response = await client.get("/api/v1/dashboard/realtime")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_ability_distribution(client, test_db):
    """Test ability distribution endpoint"""
    response = await client.get("/api/v1/dashboard/ability-distribution")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_training_trend(client, test_db):
    """Test training trend endpoint"""
    response = await client.get("/api/v1/dashboard/training-trend")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_training_trend_with_days(client, test_db):
    """Test training trend with custom days"""
    response = await client.get("/api/v1/dashboard/training-trend?days=14")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 14


@pytest.mark.asyncio
async def test_dashboard_class_comparison(client, test_db):
    """Test class comparison endpoint"""
    response = await client.get("/api/v1/dashboard/class-comparison")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_alerts(client, test_db):
    """Test alerts endpoint"""
    response = await client.get("/api/v1/dashboard/alerts")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_alerts_with_limit(client, test_db):
    """Test alerts with custom limit"""
    response = await client.get("/api/v1/dashboard/alerts?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
