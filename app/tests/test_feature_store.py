import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_feature_group(client: AsyncClient):
    token = await register_and_login(client, "fstore1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/feature-store/groups",
        headers=headers,
        json={"name": "user_features", "description": "User behavior features", "tags": ["user"]},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "user_features"


@pytest.mark.asyncio
async def test_list_feature_groups(client: AsyncClient):
    token = await register_and_login(client, "fstore2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/feature-store/groups",
        headers=headers,
        json={"name": "list_group"},
    )

    response = await client.get("/api/v1/feature-store/groups", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_add_feature_to_group(client: AsyncClient):
    token = await register_and_login(client, "fstore3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_res = await client.post(
        "/api/v1/feature-store/groups",
        headers=headers,
        json={"name": "feat_group"},
    )
    group_id = group_res.json()["id"]

    response = await client.post(
        f"/api/v1/feature-store/groups/{group_id}/features",
        headers=headers,
        json={"name": "age", "data_type": "integer"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_ingest_and_get_features(client: AsyncClient):
    token = await register_and_login(client, "fstore4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_res = await client.post(
        "/api/v1/feature-store/groups",
        headers=headers,
        json={"name": "ingest_group"},
    )
    group_id = group_res.json()["id"]

    await client.post(
        f"/api/v1/feature-store/groups/{group_id}/features",
        headers=headers,
        json={"name": "score", "data_type": "float"},
    )

    ingest_res = await client.post(
        f"/api/v1/feature-store/groups/{group_id}/ingest",
        headers=headers,
        json={"row_key": "user_001", "features": {"score": 95.5}},
    )
    assert ingest_res.status_code == 200

    get_res = await client.get(
        f"/api/v1/feature-store/groups/{group_id}/get/user_001",
        headers=headers,
    )
    assert get_res.status_code == 200
