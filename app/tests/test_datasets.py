import pytest
import io
from httpx import AsyncClient


@pytest.fixture
def sample_csv():
    csv_content = """feature1,feature2,feature3,target
1.0,2.0,3.0,class_a
4.0,5.0,6.0,class_b
7.0,8.0,9.0,class_a
10.0,11.0,12.0,class_b
"""
    return io.BytesIO(csv_content.encode())


@pytest.mark.asyncio
async def test_upload_dataset(client: AsyncClient, sample_csv):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.csv", sample_csv, "text/csv")},
        data={"name": "Test Dataset", "target_column": "target"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Dataset"
    assert data["rows_count"] == 4
    assert data["columns_count"] == 4


@pytest.mark.asyncio
async def test_list_datasets(client: AsyncClient, sample_csv):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "list@example.com",
            "username": "listuser",
            "password": "password123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "list@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    await client.post(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.csv", sample_csv, "text/csv")},
        data={"name": "Dataset 1"},
    )

    response = await client.get(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_upload_invalid_file(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid@example.com",
            "username": "invaliduser",
            "password": "password123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "invalid@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", io.BytesIO(b"invalid data"), "text/plain")},
        data={"name": "Invalid Dataset"},
    )
    assert response.status_code == 400
