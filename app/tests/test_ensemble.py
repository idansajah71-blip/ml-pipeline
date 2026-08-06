import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_ensemble(client: AsyncClient):
    token = await register_and_login(client, "ens1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model1 = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Model A", "algorithm": "random_forest", "target_column": "target"},
    )
    model2 = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "Model B", "algorithm": "decision_tree", "target_column": "target"},
    )

    response = await client.post(
        "/api/v1/ensemble",
        headers=headers,
        json={
            "name": "Test Ensemble",
            "model_ids": [model1.json()["id"], model2.json()["id"]],
            "strategy": "voting",
        },
    )
    assert response.status_code == 201
    assert response.json()["strategy"] == "voting"


@pytest.mark.asyncio
async def test_list_ensembles(client: AsyncClient):
    token = await register_and_login(client, "ens2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    model1 = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "M1", "algorithm": "random_forest", "target_column": "target"},
    )
    model2 = await client.post(
        "/api/v1/models",
        headers=headers,
        json={"name": "M2", "algorithm": "decision_tree", "target_column": "target"},
    )

    await client.post(
        "/api/v1/ensemble",
        headers=headers,
        json={
            "name": "List Ensemble",
            "model_ids": [model1.json()["id"], model2.json()["id"]],
            "strategy": "averaging",
        },
    )

    response = await client.get("/api/v1/ensemble", headers=headers)
    assert response.status_code == 200
