import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_serving_endpoint(client: AsyncClient):
    token = await register_and_login(client, "serve1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Serve Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    response = await client.post(
        "/api/v1/serving/endpoints",
        headers=headers,
        json={"name": "test-endpoint", "model_id": model_id},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "test-endpoint"


@pytest.mark.asyncio
async def test_list_serving_endpoints(client: AsyncClient):
    token = await register_and_login(client, "serve2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "List Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    await client.post(
        "/api/v1/serving/endpoints",
        headers=headers,
        json={"name": "list-ep", "model_id": model_id},
    )

    response = await client.get("/api/v1/serving/endpoints", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_serving_endpoint(client: AsyncClient):
    token = await register_and_login(client, "serve3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Del Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    ep_res = await client.post(
        "/api/v1/serving/endpoints",
        headers=headers,
        json={"name": "del-ep", "model_id": model_id},
    )
    ep_id = ep_res.json()["id"]

    response = await client.delete(f"/api/v1/serving/endpoints/{ep_id}", headers=headers)
    assert response.status_code == 200
