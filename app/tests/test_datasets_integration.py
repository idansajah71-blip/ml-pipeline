import pytest
from httpx import AsyncClient
from io import BytesIO


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "ds_inttest@example.com",
            "username": "ds_inttest",
            "password": "testpassword123",
            "full_name": "Dataset Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ds_inttest@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


def create_csv_file() -> BytesIO:
    content = "feature1,feature2,feature3,target\n1.0,2.0,3.0,0\n4.0,5.0,6.0,1\n7.0,8.0,9.0,0\n"
    return BytesIO(content.encode())


@pytest.mark.asyncio
async def test_upload_and_get_dataset(client: AsyncClient):
    token = await register_and_login(client)

    csv_file = create_csv_file()
    upload_response = await client.post(
        "/api/v1/datasets",
        files={"file": ("test.csv", csv_file, "text/csv")},
        data={"name": "Integration Test Dataset", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_response.status_code == 201
    dataset_id = upload_response.json()["id"]

    get_response = await client.get(
        f"/api/v1/datasets/{dataset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Integration Test Dataset"


@pytest.mark.asyncio
async def test_preview_dataset(client: AsyncClient):
    token = await register_and_login(client)

    csv_file = create_csv_file()
    upload_response = await client.post(
        "/api/v1/datasets",
        files={"file": ("preview_test.csv", csv_file, "text/csv")},
        data={"name": "Preview Test Dataset", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    dataset_id = upload_response.json()["id"]

    preview_response = await client.get(
        f"/api/v1/datasets/{dataset_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert preview_response.status_code == 200
    data = preview_response.json()
    assert "data" in data or "preview" in data or "columns" in data


@pytest.mark.asyncio
async def test_delete_dataset(client: AsyncClient):
    token = await register_and_login(client)

    csv_file = create_csv_file()
    upload_response = await client.post(
        "/api/v1/datasets",
        files={"file": ("delete_test.csv", csv_file, "text/csv")},
        data={"name": "Delete Test Dataset", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )
    dataset_id = upload_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/datasets/{dataset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code in (200, 204)

    get_response = await client.get(
        f"/api/v1/datasets/{dataset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_all_datasets(client: AsyncClient):
    token = await register_and_login(client)

    csv_file = create_csv_file()
    await client.post(
        "/api/v1/datasets",
        files={"file": ("list_test.csv", csv_file, "text/csv")},
        data={"name": "List Test Dataset", "target_column": "target"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get(
        "/api/v1/datasets/all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient):
    csv_file = create_csv_file()
    response = await client.post(
        "/api/v1/datasets",
        files={"file": ("test.csv", csv_file, "text/csv")},
        data={"name": "Unauthorized Dataset", "target_column": "target"},
    )
    assert response.status_code in (401, 403)
