"""Tests para la validación del API Gateway (x-api-key)."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.config import settings


@pytest.mark.asyncio
async def test_gateway_validation_excepted_routes(client: AsyncClient):
    """Las rutas exceptuadas como health check deben responder 200 sin x-api-key."""
    with patch.object(settings, "ENABLE_GATEWAY_VALIDATION", True):
        response = await client.get("/api/v1/hce/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_gateway_validation_blocked_without_header(client: AsyncClient):
    """Las rutas de negocio deben responder 403 si falta la x-api-key en producción."""
    with patch.object(settings, "ENABLE_GATEWAY_VALIDATION", True):
        # Intentamos acceder a pacientes sin header x-api-key
        response = await client.get("/api/v1/pacientes")
        assert response.status_code == 403
        assert "Acceso denegado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_gateway_validation_allowed_with_header(client: AsyncClient):
    """Las rutas de negocio deben responder con su código normal (ej: 401 si falta JWT, pero no 403) con la x-api-key correcta."""
    with patch.object(settings, "ENABLE_GATEWAY_VALIDATION", True):
        with patch.object(settings, "GATEWAY_API_KEY", "hce-secret-key"):
            # Pasamos la x-api-key correcta, pero no el JWT. Debería darnos 401 (autorización normal), no 403.
            headers = {"x-api-key": "hce-secret-key"}
            response = await client.get("/api/v1/pacientes", headers=headers)
            assert response.status_code == 401
            assert response.status_code != 403


@pytest.mark.asyncio
async def test_gateway_validation_disabled_by_default(client: AsyncClient):
    """Por defecto en desarrollo la validación está apagada, por lo que responde 401 (falta JWT) y no 403."""
    response = await client.get("/api/v1/pacientes")
    assert response.status_code == 401
    assert response.status_code != 403
