"""
Student API tests
"""
import pytest


@pytest.mark.asyncio
async def test_get_student_profile(client, student_headers):
    """Test get student profile"""
    response = await client.get("/api/v1/students/me", headers=student_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["student_no"] == "2023010101"
    assert data["name"] == "Test Student"


@pytest.mark.asyncio
async def test_get_student_records_empty(client, student_headers):
    """Test get training records when empty"""
    response = await client.get("/api/v1/students/me/training-records", headers=student_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_student_ability_map(client, student_headers):
    """Test get ability map"""
    response = await client.get("/api/v1/students/me/ability-map", headers=student_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "radar_data" in data
    assert "total_score" in data


@pytest.mark.asyncio
async def test_get_student_reports_empty(client, student_headers):
    """Test get reports when empty"""
    response = await client.get("/api/v1/students/me/reports", headers=student_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_graduation_progress(client, student_headers):
    """Test get graduation progress"""
    response = await client.get("/api/v1/students/me/graduation-progress", headers=student_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_progress" in data
    assert "graduation_ready" in data


@pytest.mark.asyncio
async def test_student_profile_unauthorized(client):
    """Test student profile without auth"""
    response = await client.get("/api/v1/students/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_student_profile_wrong_role(client, auth_headers):
    """Test student endpoint with non-student role"""
    # auth_headers is admin role, should fail
    response = await client.get("/api/v1/students/me", headers=auth_headers)
    
    assert response.status_code == 403
