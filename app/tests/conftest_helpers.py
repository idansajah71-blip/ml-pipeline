from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
import pytest

from app.main import app
from app.core.database import async_session_factory
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_user(db_session) -> User:
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.DATA_SCIENTIST,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session) -> User:
    user = User(
        email="admin@example.com",
        username="testadmin",
        full_name="Test Admin",
        hashed_password=get_password_hash("adminpass123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def user_token(test_user) -> str:
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture
def admin_token(test_admin) -> str:
    return create_access_token({"sub": str(test_admin.id)})


@pytest.fixture
def auth_headers(user_token) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
