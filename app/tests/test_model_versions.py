import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_model_version(client: AsyncClient):
    token = await register_and_login(client, "ver1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Version Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    response = await client.post(
        "/api/v1/model-versions",
        headers=headers,
        json={"model_id": model_id, "changelog": "Initial version"},
    )
    assert response.status_code == 201
    assert response.json()["version_number"] == 1


@pytest.mark.asyncio
async def test_list_model_versions(client: AsyncClient):
    token = await register_and_login(client, "ver2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "List Versions", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    await client.post(
        "/api/v1/model-versions",
        headers=headers,
        json={"model_id": model_id, "changelog": "V1"},
    )

    response = await client.get(f"/api/v1/model-versions/model/{model_id}", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_promote_model_version(client: AsyncClient):
    token = await register_and_login(client, "ver3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model_res = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Promote Model", "algorithm": "random_forest", "target_column": "target"},
    )
    model_id = model_res.json()["id"]

    ver_res = await client.post(
        "/api/v1/model-versions",
        headers=headers,
        json={"model_id": model_id, "changelog": "To promote"},
    )
    version_id = ver_res.json()["id"]

    response = await client.put(
        f"/api/v1/model-versions/{version_id}/promote",
        headers=headers,
    )
    assert response.status_code == 200
