import pytest
from httpx import AsyncClient
from io import BytesIO
from app.models.user import UserRole


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "model_inttest@example.com",
            "username": "model_inttest",
            "password": "testpassword123",
            "full_name": "Model Test User",
            "role": UserRole.DATA_SCIENTIST,
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "model_inttest@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


def create_csv_file() -> BytesIO:
    content = "feature1,feature2,feature3,target\n1.0,2.0,3.0,0\n4.0,5.0,6.0,1\n7.0,8.0,9.0,0\n10.0,11.0,12.0,1\n"
    return BytesIO(content.encode())


@pytest.mark.asyncio
async def test_create_and_get_model(client: AsyncClient):
    token = await register_and_login(client)

    create_response = await client.post(
        "/api/v1/models",
        json={
            "name": "Integration Test Model",
            "algorithm": "random_forest",
            "target_column": "target",
            "description": "Test model for integration tests",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    model_id = create_response.json()["id"]

    get_response = await client.get(
        f"/api/v1/models/{model_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Integration Test Model"


@pytest.mark.asyncio
async def test_update_model(client: AsyncClient):
    token = await register_and_login(client)

    create_response = await client.post(
        "/api/v1/models",
        json={
            "name": "Update Test Model",
            "algorithm": "logistic_regression",
            "target_column": "target",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    model_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/models/{model_id}",
        json={"name": "Updated Model Name", "description": "Updated description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Model Name"


@pytest.mark.asyncio
async def test_delete_model(client: AsyncClient):
    token = await register_and_login(client)

    create_response = await client.post(
        "/api/v1/models",
        json={
            "name": "Delete Test Model",
            "algorithm": "decision_tree",
            "target_column": "target",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    model_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/models/{model_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code in (200, 204)

    get_response = await client.get(
        f"/api/v1/models/{model_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_model_versions(client: AsyncClient):
    token = await register_and_login(client)

    create_response = await client.post(
        "/api/v1/models",
        json={
            "name": "Version Test Model",
            "algorithm": "random_forest",
            "target_column": "target",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    model_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/models/{model_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_compare_models(client: AsyncClient):
    token = await register_and_login(client)

    create_a = await client.post(
        "/api/v1/models",
        json={"name": "Model A", "algorithm": "random_forest", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    create_b = await client.post(
        "/api/v1/models",
        json={"name": "Model B", "algorithm": "logistic_regression", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    model_a_id = create_a.json()["id"]
    model_b_id = create_b.json()["id"]

    response = await client.get(
        f"/api/v1/models/compare/{model_a_id}/{model_b_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_train_model(client: AsyncClient):
    token = await register_and_login(client)

    csv_file = create_csv_file()
    upload_response = await client.post(
        "/api/v1/datasets",
        files={"file": ("train_test.csv", csv_file, "text/csv")},
        data={"name": "Train Test Dataset", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    dataset_id = upload_response.json()["id"]

    create_response = await client.post(
        "/api/v1/models",
        json={
            "name": "Train Test Model",
            "algorithm": "random_forest",
            "target_column": "target",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    model_id = create_response.json()["id"]

    train_response = await client.post(
        f"/api/v1/models/{model_id}/train",
        json={"dataset_id": dataset_id, "algorithm": "random_forest"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert train_response.status_code in (200, 202)


@pytest.mark.asyncio
async def test_model_algorithms(client: AsyncClient):
    response = await client.get("/api/v1/algorithms")
    assert response.status_code == 200
    algorithms = response.json()
    assert "classification" in algorithms
    assert "random_forest" in algorithms["classification"]["algorithms"]
    assert "logistic_regression" in algorithms["classification"]["algorithms"]
    assert len(algorithms["classification"]["algorithms"]) >= 9


@pytest.mark.asyncio
async def test_unauthorized_model_access(client: AsyncClient):
    response = await client.get("/api/v1/models")
    assert response.status_code in (401, 403)
