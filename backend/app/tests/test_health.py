"""Tests for SentinelAI health-check endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_health_check_returns_liveness() -> None:
    """The liveness endpoint should respond without external dependencies."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sentinelai-backend"}
