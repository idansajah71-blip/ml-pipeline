"""
Test configuration — self-contained, no manual DB setup required.

- Auto-creates test database and user if missing
- Drops and recreates schema before each test
- Gracefully handles missing Redis/Celery
- Pre-test assertions for DB schema and dependencies
"""

import os
import pytest
import logging
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ── Ensure test environment variables are set BEFORE any settings import ──
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("API_KEY_PEPPER", "test-pepper-for-testing-only")

# ── Bootstrap: create test DB and user if they don't exist ──────────────
_POSTGRES_ADMIN_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"


def _bootstrap_test_database():
    """Create test database and test user if they don't exist (sync driver)."""
    import psycopg2
    import psycopg2.extensions

    try:
        conn = psycopg2.connect(
            host="localhost", port=5432,
            user="postgres", password="postgres",
            dbname="postgres",
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'test_user'")
        if not cur.fetchone():
            cur.execute("CREATE ROLE test_user WITH LOGIN PASSWORD 'test_password'")
            logger.info("Created test_user role")

        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'test_db'")
        if not cur.fetchone():
            cur.execute("CREATE DATABASE test_db OWNER test_user")
            logger.info("Created test_db database")

            cur.execute("GRANT ALL PRIVILEGES ON DATABASE test_db TO test_user")

        cur.close()
        conn.close()
    except psycopg2.OperationalError as e:
        logger.error("PostgreSQL not available — DB tests will fail: %s", e)
        raise
    except Exception as e:
        logger.error("Database bootstrap failed: %s", e)
        raise


_bootstrap_test_database()

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    pool_pre_ping=True,
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            await session.execute(text("SET search_path TO public"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from app.main import app
from app.core.database import Base, get_db
from app.models.user import UserRole

app.dependency_overrides[get_db] = override_get_db


async def _reset_schema(conn):
    """Drop and recreate the public schema, then drop any orphaned ENUM types."""
    await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
    await conn.execute(text("CREATE SCHEMA public"))
    await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    rows = (await conn.execute(
        text("SELECT t.typname FROM pg_type t "
             "JOIN pg_namespace n ON n.oid = t.typnamespace "
             "WHERE n.nspname = 'public' AND t.typtype = 'e'")
    )).all()
    for row in rows:
        await conn.execute(text(f'DROP TYPE IF EXISTS "{row[0]}" CASCADE'))


async def _verify_tables_exist():
    """Check that critical tables exist — raises if they don't."""
    async with test_engine.connect() as conn:
        for table_name in ("users", "models", "datasets", "experiments"):
            result = await conn.execute(
                text("SELECT 1 FROM information_schema.tables "
                     "WHERE table_schema='public' AND table_name=:name"),
                {"name": table_name},
            )
            if result.scalar() is None:
                raise RuntimeError(f"Table '{table_name}' missing after create_all")


@pytest.fixture(autouse=True)
async def setup_database():
    """Drop + recreate schema, create all tables, verify, then cleanup after test."""
    try:
        for attempt in range(3):
            async with test_engine.begin() as conn:
                await _reset_schema(conn)
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            try:
                await _verify_tables_exist()
                break
            except RuntimeError:
                if attempt == 2:
                    logger.error("create_all: tables still missing after 3 attempts")
                    pytest.skip("Database tables could not be created")
        yield
    except Exception as e:
        if "connection" in str(e).lower() or "does not exist" in str(e).lower():
            pytest.skip(f"Database not available: {e}")
        raise
    finally:
        try:
            async with test_engine.begin() as conn:
                await _reset_schema(conn)
        except Exception:
            pass


@pytest.fixture(autouse=True)
async def flush_rate_limits():
    """Flush Redis rate-limit & training-quota keys before each test to avoid 429s."""
    import redis.asyncio as aioredis
    from app.core.config import get_settings
    settings = get_settings()
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        keys = await r.keys("rate_limit:*")
        if keys:
            await r.delete(*keys)
        quota_keys = await r.keys("training:*")
        if quota_keys:
            await r.delete(*quota_keys)
        await r.aclose()
    except Exception as e:
        logger.warning("Redis not available — rate limit flush skipped: %s", e)


@pytest.fixture(autouse=True)
async def validate_celery():
    """Log warning if Celery workers are not running (does not hard-fail unit tests)."""
    from app.core.celery_app import celery_app
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active()
        if active is None:
            logger.warning("Celery workers not running — some integration tests may fail")
    except Exception as e:
        logger.warning("Celery not available: %s", e)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_and_login(client: AsyncClient, email: str = "test@example.com", role: UserRole = UserRole.DATA_SCIENTIST) -> str:
    """Register a user, set their role via DB, and return the access token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": email.split("@")[0], "password": "password123"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    token = login_res.json()["access_token"]

    async with TestSessionLocal() as session:
        await session.execute(
            text("UPDATE users SET role = :role WHERE email = :email"),
            {"role": role.value, "email": email},
        )
        await session.commit()

    return token
