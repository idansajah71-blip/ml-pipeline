import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "monitor_inttest@example.com",
            "username": "monitor_inttest",
            "password": "testpassword123",
            "full_name": "Monitor Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "monitor_inttest@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_get_system_info(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/monitoring/system",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (200, 403)


@pytest.mark.asyncio
async def test_get_stats(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/monitoring/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (200, 403)


@pytest.mark.asyncio
async def test_unauthorized_monitoring(client: AsyncClient):
    response = await client.get("/api/v1/monitoring/stats")
    assert response.status_code in (401, 403)

    response = await client.get("/api/v1/monitoring/system")
    assert response.status_code in (401, 403)
