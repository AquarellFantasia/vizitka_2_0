"""First test suite for the simple backend."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client():
    """Create async test client."""
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_root_returns_hello(client: AsyncClient):
    """Root endpoint returns greeting."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello, World!"


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    """Health endpoint returns status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
