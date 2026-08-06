import pytest
from httpx import AsyncClient
from app.tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_organization(client: AsyncClient):
    token = await register_and_login(client, "org1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/orgs",
        headers=headers,
        json={"name": "Test Org", "slug": "test-org"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_list_organizations(client: AsyncClient):
    token = await register_and_login(client, "org2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/orgs",
        headers=headers,
        json={"name": "List Org", "slug": "list-org"},
    )

    response = await client.get("/api/v1/orgs", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_organization(client: AsyncClient):
    token = await register_and_login(client, "org3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/orgs",
        headers=headers,
        json={"name": "Get Org", "slug": "get-org"},
    )
    org_id = create_res.json()["id"]

    response = await client.get(f"/api/v1/orgs/{org_id}", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_org_members(client: AsyncClient):
    token = await register_and_login(client, "org4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/orgs",
        headers=headers,
        json={"name": "Members Org", "slug": "members-org"},
    )
    org_id = create_res.json()["id"]

    response = await client.get(f"/api/v1/orgs/{org_id}/members", headers=headers)
    assert response.status_code == 200
