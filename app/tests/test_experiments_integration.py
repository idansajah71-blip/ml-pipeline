import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "exp_inttest@example.com",
            "username": "exp_inttest",
            "password": "testpassword123",
            "full_name": "Experiment Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "exp_inttest@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_list_experiments(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/experiments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data


@pytest.mark.asyncio
async def test_unauthorized_experiments(client: AsyncClient):
    response = await client.get("/api/v1/experiments")
    assert response.status_code in (401, 403)
