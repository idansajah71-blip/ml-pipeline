import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from app.models.user import UserRole
from app.services import system_health
from app.services.system_health import (
    STATUS_OK,
    STATUS_DEGRADED,
    STATUS_ERROR,
    check_database,
    check_redis,
    check_celery,
    check_storage_sync,
    check_system_health,
    is_celery_available,
)
from app.tests.conftest import register_and_login


# ── Unit tests ──────────────────────────────────────────────────────────────

class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, *args, **kwargs):
        return MagicMock()


@pytest.mark.asyncio
async def test_check_database_ok():
    with patch.object(system_health, "async_session_factory", lambda: _FakeSession()):
        result = await check_database()
    assert result["status"] == STATUS_OK
    assert result["name"] == "Database"
    assert result["latency_ms"] is not None


@pytest.mark.asyncio
async def test_check_database_error():
    def broken_factory():
        raise ConnectionError("connection refused")

    with patch.object(system_health, "async_session_factory", broken_factory):
        result = await check_database()
    assert result["status"] == STATUS_ERROR
    assert "detail_error" in result


@pytest.mark.asyncio
async def test_check_redis_ok():
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    with patch.object(system_health, "get_redis", AsyncMock(return_value=client)):
        result = await check_redis()
    assert result["status"] == STATUS_OK


@pytest.mark.asyncio
async def test_check_redis_unavailable():
    with patch.object(system_health, "get_redis", AsyncMock(return_value=None)):
        result = await check_redis()
    assert result["status"] == STATUS_ERROR


@pytest.mark.asyncio
async def test_check_redis_error():
    client = AsyncMock()
    client.ping = AsyncMock(side_effect=ConnectionError("connection refused"))
    with patch.object(system_health, "get_redis", AsyncMock(return_value=client)):
        result = await check_redis()
    assert result["status"] == STATUS_ERROR


def test_is_celery_available_stub(monkeypatch):
    class Stub:
        def __getattr__(self, item):
            return None

    monkeypatch.setattr("app.core.celery_app.celery_app", Stub())
    assert is_celery_available() is False


def test_is_celery_available_real(monkeypatch):
    fake = MagicMock()
    fake.control = MagicMock()
    fake.task = MagicMock()
    monkeypatch.setattr("app.core.celery_app.celery_app", fake)
    assert is_celery_available() is True


@pytest.mark.asyncio
async def test_check_celery_not_installed(monkeypatch):
    monkeypatch.setattr(system_health, "is_celery_available", lambda: False)
    result = await check_celery()
    assert result["status"] == STATUS_DEGRADED
    assert result["worker_count"] == 0


@pytest.mark.asyncio
async def test_check_celery_no_workers(monkeypatch):
    monkeypatch.setattr(system_health, "is_celery_available", lambda: True)
    fake = MagicMock()
    fake.control.ping.return_value = []
    monkeypatch.setattr("app.core.celery_app.celery_app", fake)
    result = await check_celery()
    assert result["status"] == STATUS_DEGRADED


@pytest.mark.asyncio
async def test_check_celery_with_workers(monkeypatch):
    monkeypatch.setattr(system_health, "is_celery_available", lambda: True)
    fake = MagicMock()
    fake.control.ping.return_value = [{"celery@worker1": {"ok": "pong"}}]
    monkeypatch.setattr("app.core.celery_app.celery_app", fake)
    result = await check_celery()
    assert result["status"] == STATUS_OK
    assert result["worker_count"] == 1


@pytest.mark.asyncio
async def test_check_celery_broker_down(monkeypatch):
    monkeypatch.setattr(system_health, "is_celery_available", lambda: True)
    fake = MagicMock()
    fake.control.ping.side_effect = ConnectionError("connection refused")
    monkeypatch.setattr("app.core.celery_app.celery_app", fake)
    result = await check_celery()
    assert result["status"] == STATUS_ERROR


def test_check_storage_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(system_health.settings, "ML_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda p: (100 * 1024 ** 3, 20 * 1024 ** 3, 80 * 1024 ** 3),
    )
    result = check_storage_sync()
    assert result["status"] == STATUS_OK
    assert result["artifact_count"] == 0
    assert result["used_pct"] == 20.0


def test_check_storage_almost_full(tmp_path, monkeypatch):
    monkeypatch.setattr(system_health.settings, "ML_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda p: (100 * 1024 ** 3, 95 * 1024 ** 3, 5 * 1024 ** 3),
    )
    result = check_storage_sync()
    assert result["status"] == STATUS_DEGRADED


def test_check_storage_not_writable(tmp_path, monkeypatch):
    # Simulate unwritable dir by pointing at a file path.
    blocked = tmp_path / "not_a_dir"
    blocked.write_text("x")
    monkeypatch.setattr(system_health.settings, "ML_ARTIFACTS_DIR", str(blocked))
    result = check_storage_sync()
    # makedirs on an existing file raises OSError → treated as error.
    assert result["status"] in (STATUS_ERROR, STATUS_DEGRADED)


@pytest.mark.asyncio
async def test_check_system_health_overall_error():
    async def fake_db():
        return {"name": "Database", "status": STATUS_OK}

    async def fake_redis():
        return {"name": "Redis", "status": STATUS_OK}

    async def fake_celery():
        return {"name": "Celery", "status": STATUS_ERROR}

    with patch.object(system_health, "check_database", fake_db), \
         patch.object(system_health, "check_redis", fake_redis), \
         patch.object(system_health, "check_celery", fake_celery), \
         patch.object(system_health, "check_storage_sync", lambda: {"name": "Storage", "status": STATUS_OK}), \
         patch.object(system_health, "check_system_resources", fake_db):
        report = await check_system_health()

    assert report["status"] == STATUS_ERROR
    assert report["summary"]["error"] == 1
    assert len(report["components"]) == 5
    assert "checked_at" in report


@pytest.mark.asyncio
async def test_check_system_health_overall_degraded():
    async def fake_ok():
        return {"name": "X", "status": STATUS_OK}

    async def fake_degraded():
        return {"name": "Celery", "status": STATUS_DEGRADED}

    with patch.object(system_health, "check_database", fake_ok), \
         patch.object(system_health, "check_redis", fake_ok), \
         patch.object(system_health, "check_celery", fake_degraded), \
         patch.object(system_health, "check_storage_sync", lambda: {"name": "Storage", "status": STATUS_OK}), \
         patch.object(system_health, "check_system_resources", fake_ok):
        report = await check_system_health()

    assert report["status"] == STATUS_DEGRADED
    assert report["summary"]["degraded"] == 1


# ── Endpoint tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_system_health_requires_admin(client: AsyncClient):
    token = await register_and_login(client, email="health_user@example.com")
    response = await client.get(
        "/api/v1/admin/system-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_system_health_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/admin/system-health")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_system_health_admin_ok(client: AsyncClient):
    token = await register_and_login(
        client, email="health_admin@example.com", role=UserRole.ADMIN
    )
    response = await client.get(
        "/api/v1/admin/system-health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "summary" in data
    names = {c["name"] for c in data["components"]}
    assert {"Database", "Redis", "Celery", "Storage", "Server"} <= names
