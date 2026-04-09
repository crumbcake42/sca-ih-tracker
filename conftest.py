"""
Root conftest — fixtures available to all tests regardless of location.

Why here and not in tests/?
Pytest walks the directory tree upward from each test file looking for
conftest.py files. A root-level conftest is the only place that's
guaranteed to be found by both tests/ (integration) and app/**/test_*.py
(colocated unit tests).
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.users.dependencies import get_current_user

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


# Module scope: create the schema once per test file, not once per test.
# Each test still gets its own session that rolls back, so tests are isolated
# without paying the schema-creation cost on every function.
@pytest.fixture(scope="module")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession]:
    # Wrap every test in a transaction that rolls back on teardown.
    # This is faster than truncating tables and avoids needing a separate
    # "cleanup" fixture for every test that writes to the DB.
    async with test_engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            yield session
        await conn.rollback()


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession):
    """Unauthenticated client — use to test 401 responses."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(db_session: AsyncSession):
    """
    Authenticated client with a fake superadmin user.

    Why override get_current_user instead of issuing a real JWT?
    Issuing a real token requires the users/roles/permissions tables to be
    populated and a working auth flow — that's setup state which has nothing
    to do with the endpoint under test. Overriding the dependency injects a
    realistic User object directly, making test intent clearer and setup
    cheaper.
    """
    from app.common.enums import PermissionName
    from app.users.models import Permission, Role, User

    fake_permissions = [
        Permission(id=i, name=p.value) for i, p in enumerate(PermissionName, 1)
    ]
    fake_role = Role(id=1, name="superadmin", permissions=fake_permissions)
    fake_user = User(
        id=1,
        first_name="Test",
        last_name="User",
        username="testuser",
        email="test@example.com",
        hashed_password="irrelevant",
        role_id=1,
        role=fake_role,
    )

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
