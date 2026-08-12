import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import update as sa_update, text

from app.main import app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.models.user import User, UserRole

settings = get_settings()

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"

# NullPool: each session gets a fresh connection and returns it immediately,
# avoiding the asyncpg pool-teardown race that caused flaky IntegrityError/
# AttributeError when dispose() ran while pooled connections were in flight.
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
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        # 1. Drop all tables first (removes FK dependencies on ENUMs)
        await conn.run_sync(Base.metadata.drop_all)
        # 2. Drop orphaned Postgres ENUM types left by previous runs
        rows = (
            await conn.execute(text(
                "SELECT t.typname FROM pg_type t "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE n.nspname = 'public' AND t.typtype = 'e'"
            ))
        ).all()
        for row in rows:
            await conn.execute(text(f'DROP TYPE IF EXISTS "{row[0]}" CASCADE'))
        # 3. Create everything fresh
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        rows = (
            await conn.execute(text(
                "SELECT t.typname FROM pg_type t "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE n.nspname = 'public' AND t.typtype = 'e'"
            ))
        ).all()
        for row in rows:
            await conn.execute(text(f'DROP TYPE IF EXISTS "{row[0]}" CASCADE'))
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def flush_rate_limits():
    """Flush Redis rate-limit & training-quota keys before each test to avoid 429s.

    The middleware uses get_redis() → settings.REDIS_URL (db 0), so the old
    hardcoded db 1 never actually cleared the counters that caused 429s.
    """
    import redis.asyncio as aioredis
    from app.core.config import get_settings
    try:
        r = aioredis.from_url(get_settings().REDIS_URL)
        keys = await r.keys("rate_limit:*")
        if keys:
            await r.delete(*keys)
        quota_keys = await r.keys("training:*")
        if quota_keys:
            await r.delete(*quota_keys)
        await r.aclose()
    except Exception:
        pass


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

    # Update role in a fresh session
    async with TestSessionLocal() as session:
        await session.execute(
            sa_update(User).where(User.email == email).values(role=role)
        )
        await session.commit()

    return token
