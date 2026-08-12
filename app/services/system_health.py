"""System health checks for the internal admin dashboard.

Every check returns a structured payload and NEVER raises — the dashboard
must stay available even when the components it inspects are down.
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

settings = get_settings()

CHECK_TIMEOUT_SECONDS = 8

STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_ERROR = "error"


def _result(
    status: str,
    name: str,
    detail: str = "",
    latency_ms: Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": name,
        "status": status,
        "detail": detail,
        "latency_ms": latency_ms,
    }
    payload.update(extra)
    return payload


def is_celery_available() -> bool:
    """True when a real Celery app (with a control interface) is available.

    The Celery stub used when celery is not installed exposes a __getattr__
    that returns callables for everything, so we must probe one level deeper
    (control.ping) to tell a real app from the stub.
    """
    try:
        from app.core.celery_app import celery_app as celery

        control = getattr(celery, "control", None)
        if control is None or not callable(getattr(control, "ping", None)):
            return False
        return True
    except Exception:
        return False


def check_storage_sync() -> Dict[str, Any]:
    """Storage check (disk space + artifacts dir writability)."""
    start = time.monotonic()
    artifacts_dir = settings.ML_ARTIFACTS_DIR
    detail_parts = []
    extra: Dict[str, Any] = {}

    try:
        os.makedirs(artifacts_dir, exist_ok=True)
    except OSError as e:
        return _result(
            STATUS_ERROR,
            "Storage",
            "Direktori penyimpanan model tidak dapat dibuat.",
            detail_error=str(e)[:200],
        )

    writable = os.access(artifacts_dir, os.W_OK)
    artifact_count = 0
    try:
        artifact_count = len(
            [f for f in os.listdir(artifacts_dir) if os.path.isdir(os.path.join(artifacts_dir, f))]
        )
    except OSError:
        pass
    extra["artifact_count"] = artifact_count

    try:
        import shutil

        total, used, free = shutil.disk_usage(artifacts_dir)
        total_gb = total / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        used_pct = round((used / total) * 100, 1) if total else 0.0
        extra["total_gb"] = round(total_gb, 1)
        extra["free_gb"] = round(free_gb, 1)
        extra["used_pct"] = used_pct
        detail_parts.append(f"Disk {used_pct}% terpakai ({free_gb:.1f} GB tersedia)")
    except Exception:
        extra["used_pct"] = None

    if not writable:
        return _result(
            STATUS_ERROR,
            "Storage",
            "Direktori penyimpanan model tidak dapat ditulis.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            **extra,
        )

    if extra.get("used_pct") is not None and extra["used_pct"] > 90:
        return _result(
            STATUS_DEGRADED,
            "Storage",
            "Kapasitas disk hampir penuh. Bersihkan artefak model lama.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            **extra,
        )

    detail_parts.append(f"{artifact_count} artefak model")
    return _result(
        STATUS_OK,
        "Storage",
        "Penyimpanan normal. " + ", ".join(detail_parts),
        latency_ms=round((time.monotonic() - start) * 1000, 1),
        **extra,
    )


async def check_database() -> Dict[str, Any]:
    """Database connectivity check (SELECT 1)."""
    start = time.monotonic()
    try:
        async def _probe() -> None:
            from sqlalchemy import text

            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))

        await asyncio.wait_for(_probe(), timeout=CHECK_TIMEOUT_SECONDS)
        return _result(
            STATUS_OK,
            "Database",
            "Koneksi PostgreSQL normal.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except asyncio.TimeoutError:
        return _result(
            STATUS_ERROR,
            "Database",
            "Waktu tunggu koneksi database habis.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except Exception as e:
        return _result(
            STATUS_ERROR,
            "Database",
            "Database tidak dapat dijangkau.",
            detail_error=str(e)[:200],
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


async def check_redis() -> Dict[str, Any]:
    """Redis connectivity check."""
    start = time.monotonic()
    try:
        client = await asyncio.wait_for(get_redis(), timeout=CHECK_TIMEOUT_SECONDS)
        if client is None:
            return _result(
                STATUS_ERROR,
                "Redis",
                "Layanan cache (Redis) tidak tersedia.",
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )
        await asyncio.wait_for(client.ping(), timeout=CHECK_TIMEOUT_SECONDS)
        return _result(
            STATUS_OK,
            "Redis",
            "Layanan cache normal.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except asyncio.TimeoutError:
        return _result(
            STATUS_ERROR,
            "Redis",
            "Waktu tunggu koneksi Redis habis.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except Exception as e:
        return _result(
            STATUS_ERROR,
            "Redis",
            "Layanan cache (Redis) tidak dapat dijangkau.",
            detail_error=str(e)[:200],
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


async def check_celery() -> Dict[str, Any]:
    """Celery availability check (broker reachable + at least one worker)."""
    start = time.monotonic()

    if not is_celery_available():
        return _result(
            STATUS_DEGRADED,
            "Celery",
            "Celery tidak terpasang. Pelatihan background dinonaktifkan — "
            "sistem otomatis memakai pelatihan langsung (synchronous).",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            worker_count=0,
        )

    def _ping_workers() -> list:
        from app.core.celery_app import celery_app as celery

        return celery.control.ping(timeout=2)

    try:
        workers = await asyncio.wait_for(
            asyncio.to_thread(_ping_workers), timeout=CHECK_TIMEOUT_SECONDS
        )
        worker_count = len(workers or [])
        if worker_count == 0:
            return _result(
                STATUS_DEGRADED,
                "Celery",
                "Broker antrean aktif tetapi tidak ada worker yang berjalan. "
                "Pelatihan akan dijalankan langsung (synchronous).",
                latency_ms=round((time.monotonic() - start) * 1000, 1),
                worker_count=0,
            )
        return _result(
            STATUS_OK,
            "Celery",
            f"Worker antrean normal ({worker_count} worker aktif).",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            worker_count=worker_count,
        )
    except asyncio.TimeoutError:
        return _result(
            STATUS_ERROR,
            "Celery",
            "Waktu tunggu layanan antrean (Celery) habis.",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )
    except Exception as e:
        return _result(
            STATUS_ERROR,
            "Celery",
            "Layanan antrean (Celery) tidak dapat dijangkau. "
            "Pelatihan akan dijalankan langsung (synchronous).",
            detail_error=str(e)[:200],
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


async def check_system_resources() -> Dict[str, Any]:
    """Host resource usage (CPU / memory / disk percent)."""
    start = time.monotonic()
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(settings.ML_ARTIFACTS_DIR or "/")

        if cpu > 90 or mem.percent > 90:
            status = STATUS_DEGRADED
        else:
            status = STATUS_OK

        return _result(
            status,
            "Server",
            f"CPU {cpu}% · RAM {mem.percent}% · Disk {disk.percent}%",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            cpu_percent=cpu,
            memory_percent=mem.percent,
            disk_percent=disk.percent,
        )
    except Exception as e:
        return _result(
            STATUS_DEGRADED,
            "Server",
            "Metrik server tidak tersedia.",
            detail_error=str(e)[:200],
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


async def check_system_health() -> Dict[str, Any]:
    """Run all checks and produce the full health report."""
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_celery(),
        asyncio.to_thread(check_storage_sync),
        check_system_resources(),
    )

    counts = {"ok": 0, "degraded": 0, "error": 0}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1

    if counts["error"] > 0:
        overall = STATUS_ERROR
    elif counts["degraded"] > 0:
        overall = STATUS_DEGRADED
    else:
        overall = STATUS_OK

    return {
        "status": overall,
        "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
        "environment": settings.ENVIRONMENT,
        "app_version": settings.APP_VERSION,
        "components": checks,
        "summary": {"total": len(checks), **counts},
    }
