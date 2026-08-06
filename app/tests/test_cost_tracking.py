import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_record_cost(client: AsyncClient):
    token = await register_and_login(client, "cost1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/costs",
        headers=headers,
        json={
            "resource_type": "compute",
            "cost_usd": 15.50,
            "usage_hours": 10,
            "gpu_hours": 5,
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_cost_summary(client: AsyncClient):
    token = await register_and_login(client, "cost2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/costs",
        headers=headers,
        json={"resource_type": "storage", "cost_usd": 5.0},
    )

    response = await client.get("/api/v1/costs/summary", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_costs_by_model(client: AsyncClient):
    token = await register_and_login(client, "cost3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/costs/by-model", headers=headers)
    assert response.status_code == 200
