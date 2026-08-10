import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_share_model(client: AsyncClient):
    token = await register_and_login(client, "share1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Shared Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    response = await client.post(
        "/api/v1/marketplace/share",
        headers=headers,
        json={"model_id": model_id, "is_public": True, "tags": ["demo"]},
    )
    assert response.status_code == 201
    assert response.json()["model_id"] == model_id


@pytest.mark.asyncio
async def test_discover_models(client: AsyncClient):
    token = await register_and_login(client, "discover1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Disc Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    await client.post(
        "/api/v1/marketplace/share",
        headers=headers,
        json={"model_id": model_id, "is_public": True},
    )

    response = await client.get("/api/v1/marketplace/discover", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_model(client: AsyncClient):
    token = await register_and_login(client, "rate1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Rate Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    share_res = await client.post(
        "/api/v1/marketplace/share",
        headers=headers,
        json={"model_id": model_id, "is_public": True},
    )
    share_id = share_res.json()["id"]

    # rating is a query param
    response = await client.post(
        f"/api/v1/marketplace/{share_id}/rate",
        headers=headers,
        json={"rating": 4},
    )
    assert response.status_code == 200
