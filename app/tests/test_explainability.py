import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_global_explain(client: AsyncClient):
    token = await register_and_login(client, "explain1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/explain/global",
        headers=headers,
        json={"model_id": "00000000-0000-0000-0000-000000000000", "sample_data": [{"feat1": 1}]},
    )
    assert response.status_code in (200, 404, 400)


@pytest.mark.asyncio
async def test_prediction_explain(client: AsyncClient):
    token = await register_and_login(client, "explain2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/explain/prediction",
        headers=headers,
        json={"model_id": "00000000-0000-0000-0000-000000000000", "input_data": {"feat1": 1}},
    )
    assert response.status_code in (200, 404, 400)
