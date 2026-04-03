import pytest
from app.database import get_db
from app.main import app
from httpx import AsyncClient, ASGITransport

# Use an in-memory SQLite for speed during unit tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def client(db_session):
    # Override the get_db dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Define the transport explicitly for the FastAPI app
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
