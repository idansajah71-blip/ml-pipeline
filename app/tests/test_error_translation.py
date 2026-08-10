import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.error_utils import (
    translate_error_message,
    sanitize_error_message,
    translate_http_status,
    humanize_http_detail,
    sanitize_validation_error,
)


# ── Technical message translation ───────────────────────────────────────────

def test_translate_asyncpg_message():
    msg = "asyncpg.exceptions.ConnectionDoesNotExistError: connection to server failed"
    translated = translate_error_message(msg)
    assert translated != msg
    assert "database" in translated.lower()


def test_translate_kombu_broker_down():
    msg = "kombu.exceptions.OperationalError: [Errno 111] Connection refused"
    translated = translate_error_message(msg)
    assert "sinkron" in translated.lower() or "celery" in translated.lower()


def test_translate_redis_connection_refused():
    msg = "redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379"
    translated = translate_error_message(msg)
    assert "redis" in translated.lower() or "cache" in translated.lower()


def test_translate_no_module_celery():
    msg = "No module named 'celery'"
    translated = translate_error_message(msg)
    assert "sinkron" in translated.lower()


def test_translate_unknown_message_kept():
    msg = "some unrelated message"
    assert translate_error_message(msg) == msg


def test_sanitize_never_leaks_internals():
    raw = "File \"C:\\secret\\app\\core\\database.py\", line 42\npassword=supersecret\nconnection refused"
    result = sanitize_error_message(Exception(raw))
    assert "database.py" not in result
    assert "supersecret" not in result
    assert "password" not in result


def test_sanitize_known_type_message():
    result = sanitize_error_message(ValueError("bad value"))
    assert result == "Input yang diberikan tidak valid"


def test_sanitize_translated_technical():
    result = sanitize_error_message(
        Exception("asyncpg.exceptions.InterfaceError: cannot perform operation")
    )
    assert "database" in result.lower()


# ── HTTP status translation ─────────────────────────────────────────────────

def test_translate_http_status_404():
    assert "tidak ditemukan" in translate_http_status(404)


def test_translate_http_status_500():
    assert "kesalahan internal" in translate_http_status(500)


def test_translate_http_status_unknown():
    assert "599" in translate_http_status(599)


def test_humanize_http_detail_traceback_replaced():
    raw = "Traceback (most recent call last):\n  File \"app/api/x.py\", line 10\n    raise Exception('boom')"
    assert humanize_http_detail(raw, 500) == translate_http_status(500)


def test_humanize_http_detail_technical_translated():
    result = humanize_http_detail("asyncpg.exceptions: cannot connect", 500)
    assert "database" in result.lower()


def test_humanize_http_detail_keeps_human_messages():
    assert humanize_http_detail("Model not found", 404) == "Model not found"


def test_humanize_http_detail_empty_uses_status():
    assert humanize_http_detail("", 503) == translate_http_status(503)


def test_sanitize_validation_error_forms():
    assert "invalid" in sanitize_validation_error(ValueError("invalid email")).lower()
    assert "required" in sanitize_validation_error(ValueError("field is null")).lower()


# ── Celery → sync training fallback ─────────────────────────────────────────

class _BrokerDownTask:
    """Fake Celery task whose .delay() fails like a down broker."""

    def delay(self, **kwargs):
        raise ConnectionError("kombu.exceptions.OperationalError: connection refused")


class _StubTask:
    """Fake used when Celery is not installed at all."""


def test_dispatch_raises_503_when_broker_down(monkeypatch):
    from app.services.model_service import ModelService

    monkeypatch.setattr("app.ml.tasks.train_model_task", _BrokerDownTask())
    service = ModelService(db=None)
    with pytest.raises(HTTPException) as excinfo:
        service._dispatch_async_training(
            "model-1", "exp-1", "/tmp/data.csv", "random_forest", {}, "target", "user-1"
        )
    assert excinfo.value.status_code == 503
    assert "sinkron" in excinfo.value.detail.lower()


def test_dispatch_raises_503_when_celery_stub(monkeypatch):
    from app.services.model_service import ModelService

    monkeypatch.setattr("app.ml.tasks.train_model_task", None)
    service = ModelService(db=None)
    with pytest.raises(HTTPException) as excinfo:
        service._dispatch_async_training(
            "model-1", "exp-1", "/tmp/data.csv", "random_forest", {}, "target", "user-1"
        )
    assert excinfo.value.status_code == 503


async def register_and_login(client: AsyncClient) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "fallback_test@example.com",
            "username": "fallback_test",
            "password": "testpassword123",
            "full_name": "Fallback Test User",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "fallback_test@example.com", "password": "testpassword123"},
    )
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_async_training_falls_back_to_sync_when_broker_down(client: AsyncClient, monkeypatch):
    """When Celery dispatch fails, training must continue synchronously (200, not 503)."""
    from app.tests.conftest import TestSessionLocal
    from app.models.user import User
    from sqlalchemy import update as sa_update

    token = await register_and_login(client)

    # Ensure user has the data scientist role
    async with TestSessionLocal() as session:
        await session.execute(
            sa_update(User).where(User.email == "fallback_test@example.com")
            .values(role="data_scientist")
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {token}"}

    csv_file = (
        "feature1,feature2,feature3,target\n"
        "1.0,2.0,3.0,0\n4.0,5.0,6.0,1\n7.0,8.0,9.0,0\n10.0,11.0,12.0,1\n"
        "13.0,14.0,15.0,0\n16.0,17.0,18.0,1\n19.0,20.0,21.0,0\n22.0,23.0,24.0,1\n"
    )
    from io import BytesIO

    upload = await client.post(
        "/api/v1/datasets",
        files={"file": ("fallback.csv", BytesIO(csv_file.encode()), "text/csv")},
        data={"name": "Fallback Dataset", "target_column": "target"},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    dataset_id = upload.json()["id"]

    create = await client.post(
        "/api/v1/models",
        json={
            "name": "Fallback Model",
            "algorithm": "random_forest",
            "target_column": "target",
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    model_id = create.json()["id"]

    # Break Celery dispatch → the API must fall back to synchronous training.
    monkeypatch.setattr("app.ml.tasks.train_model_task", _BrokerDownTask())

    train = await client.post(
        f"/api/v1/models/{model_id}/train",
        json={
            "dataset_id": dataset_id,
            "algorithm": "random_forest",
            "async_training": True,
        },
        headers=headers,
    )
    assert train.status_code == 200, train.text
    assert train.json()["status"] == "completed"
