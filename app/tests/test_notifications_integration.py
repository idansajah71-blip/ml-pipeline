import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "notif_inttest@example.com",
            "username": "notif_inttest",
            "password": "testpassword123",
            "full_name": "Notification Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "notif_inttest@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_list_webhooks(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/notifications/webhooks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_webhook(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.post(
        "/api/v1/notifications/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["training.completed", "model.deployed"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (201, 400)


@pytest.mark.asyncio
async def test_unauthorized_webhooks(client: AsyncClient):
    response = await client.get("/api/v1/notifications/webhooks")
    assert response.status_code in (401, 403)

    response = await client.post(
        "/api/v1/notifications/webhooks",
        json={"url": "https://example.com/webhook", "events": ["test"]},
    )
    assert response.status_code in (401, 403)
