import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_get_drift_alerts(client: AsyncClient):
    token = await register_and_login(client, "monitor1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/feature-monitoring/alerts", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_check_feature_drift(client: AsyncClient):
    token = await register_and_login(client, "monitor2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # params are query params, not body
    response = await client.post(
        "/api/v1/feature-monitoring/check?feature_name=age&current_value=25&baseline_mean=30&baseline_std=5",
        headers=headers,
    )
    assert response.status_code == 200
