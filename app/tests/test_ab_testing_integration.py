import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ab_inttest@example.com",
            "username": "ab_inttest",
            "password": "testpassword123",
            "full_name": "AB Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ab_inttest@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_list_ab_tests(client: AsyncClient):
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/ab-tests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_ab_test(client: AsyncClient):
    token = await register_and_login(client)

    create_a = await client.post(
        "/api/v1/models",
        json={"name": "AB Model A", "algorithm": "random_forest", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    create_b = await client.post(
        "/api/v1/models",
        json={"name": "AB Model B", "algorithm": "logistic_regression", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )

    if create_a.status_code == 201 and create_b.status_code == 201:
        model_a_id = create_a.json()["id"]
        model_b_id = create_b.json()["id"]

        response = await client.post(
            "/api/v1/ab-tests",
            json={
                "name": "Integration AB Test",
                "model_a_id": model_a_id,
                "model_b_id": model_b_id,
                "traffic_split": 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (201, 400)


@pytest.mark.asyncio
async def test_unauthorized_ab_tests(client: AsyncClient):
    response = await client.get("/api/v1/ab-tests")
    assert response.status_code in (401, 403)
