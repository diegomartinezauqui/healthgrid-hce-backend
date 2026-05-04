"""Tests para el endpoint de health check."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health check debe retornar 200 sin autenticación."""
    response = await client.get("/api/v1/hce/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["module"] == "hce"
    assert "timestamp" in data
