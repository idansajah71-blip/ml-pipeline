import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import update as sa_update

from app.main import app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.models.user import User, UserRole

settings = get_settings()

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=10,
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
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Dispose connections after each test to avoid stale connections
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def flush_rate_limits():
    """Flush Redis rate limit keys before each test to avoid 429s."""
    import redis.asyncio as aioredis
    try:
        r = aioredis.from_url("redis://localhost:6379/1")
        keys = await r.keys("rate_limit:*")
        if keys:
            await r.delete(*keys)
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
