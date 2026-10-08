import base64

import pytest
from sqlalchemy import select

from app.models.lab import Lab


PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


@pytest.mark.asyncio
async def test_admin_uploads_reference_image(client, test_db, auth_headers, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "REFERENCE_IMAGE_DIR", str(tmp_path))
    async with test_db() as session:
        session.add(Lab(id="lab-reference", name="标准图实训室", equipment=[]))
        await session.commit()

    response = await client.post(
        "/api/v1/environment/labs/lab-reference/reference",
        headers=auth_headers,
        files={"file": ("standard.png", PNG_1X1, "image/png")},
    )
    assert response.status_code == 200
    image_url = response.json()["reference_image_url"]
    assert image_url.startswith("/api/v1/environment/reference-images/")
    image_response = await client.get(image_url)
    assert image_response.status_code == 200
    assert image_response.content == PNG_1X1
    async with test_db() as session:
        lab = (await session.execute(select(Lab).where(Lab.id == "lab-reference"))).scalar_one()
        assert lab.reference_image_url == image_url


@pytest.mark.asyncio
async def test_student_cannot_upload_reference_image(client, test_db, student_headers, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "REFERENCE_IMAGE_DIR", str(tmp_path))
    async with test_db() as session:
        session.add(Lab(id="lab-forbidden", name="受限实训室", equipment=[]))
        await session.commit()

    response = await client.post(
        "/api/v1/environment/labs/lab-forbidden/reference",
        headers=student_headers,
        files={"file": ("standard.png", PNG_1X1, "image/png")},
    )
    assert response.status_code == 403
