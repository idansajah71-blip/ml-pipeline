import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_get_quota(client: AsyncClient):
    token = await register_and_login(client, "quota1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/quota", headers=headers)
    assert response.status_code == 200
    assert "tier" in response.json()


@pytest.mark.asyncio
async def test_check_quota(client: AsyncClient):
    token = await register_and_login(client, "quota2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/quota/check", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_tier(client: AsyncClient):
    token = await register_and_login(client, "quota3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.put(
        "/api/v1/quota/tier",
        headers=headers,
        json={"tier": "starter"},
    )
    assert response.status_code == 200
