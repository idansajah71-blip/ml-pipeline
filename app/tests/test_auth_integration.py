import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient, email: str = "inttest@example.com") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": f"user_{email.split('@')[0]}",
            "password": "testpassword123",
            "full_name": "Integration Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


async def register_admin(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin_inttest@example.com",
            "username": "admin_inttest",
            "password": "adminpassword123",
            "full_name": "Admin Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin_inttest@example.com", "password": "adminpassword123"},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient):
    token = await register_and_login(client, "update_me@example.com")

    response = await client.put(
        "/api/v1/auth/me",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_generate_api_key(client: AsyncClient):
    token = await register_and_login(client, "apikey@example.com")

    response = await client.post(
        "/api/v1/auth/api-key",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert len(data["api_key"]) > 0


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    token = await register_and_login(client, "changepw@example.com")

    response = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "testpassword123",
            "new_password": "newpassword456",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "changepw@example.com", "password": "newpassword456"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient):
    token = await register_and_login(client, "wrongpw@example.com")

    response = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (400, 401, 422)


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)
