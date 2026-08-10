import pytest
from httpx import AsyncClient
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_create_model(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "model@example.com",
            "username": "modeluser",
            "password": "password123",
            "full_name": "Model Test User",
            "role": UserRole.DATA_SCIENTIST,
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "model@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Model",
            "algorithm": "random_forest",
            "target_column": "target",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Model"
    assert data["algorithm"] == "random_forest"


@pytest.mark.asyncio
async def test_list_models(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "listmodels@example.com",
            "username": "listmodelsuser",
            "password": "password123",
            "role": UserRole.DATA_SCIENTIST,
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "listmodels@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    await client.post(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Model 1",
            "algorithm": "random_forest",
            "target_column": "target",
        },
    )

    response = await client.get(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_algorithms(client: AsyncClient):
    response = await client.get("/api/v1/algorithms")
    assert response.status_code == 200
    data = response.json()
    assert "classification" in data
    assert "random_forest" in data["classification"]["algorithms"]
