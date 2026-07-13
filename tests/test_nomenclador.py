import pytest
from httpx import AsyncClient

from app.auth.dev_auth import generate_dev_token, DevLoginRequest


@pytest.fixture
def auth_headers() -> dict:
    login_req = DevLoginRequest(
        sub=42,
        sede_id=3,
        permissions=[
            "hce:episodes:read",
        ],
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


@pytest.mark.asyncio
async def test_consultar_nomenclador_mock(client: AsyncClient, auth_headers: dict):
    # Sin filtros
    res = await client.get("/api/v1/nomenclador/prestaciones", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert data[0]["codigoNomenclador"] == "42.01.01"

    # Filtrando por tipo
    res_tipo = await client.get("/api/v1/nomenclador/prestaciones?tipo=LABORATORIO", headers=auth_headers)
    assert res_tipo.status_code == 200
    data_tipo = res_tipo.json()
    assert len(data_tipo) == 1
    assert data_tipo[0]["codigoNomenclador"] == "01.01.01"

    # Filtrando por descripción
    res_desc = await client.get("/api/v1/nomenclador/prestaciones?descripcion=general", headers=auth_headers)
    assert res_desc.status_code == 200
    data_desc = res_desc.json()
    assert len(data_desc) == 1
    assert "general" in data_desc[0]["descripcion"].lower()


@pytest.mark.asyncio
async def test_consultar_obras_sociales_mock(client: AsyncClient, auth_headers: dict):
    res = await client.get("/api/v1/nomenclador/obras-sociales", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert any(x["nombre"] == "OSDE" for x in data)


@pytest.mark.asyncio
async def test_consultar_planes_mock(client: AsyncClient, auth_headers: dict):
    # Sin filtro de entidad
    res = await client.get("/api/v1/nomenclador/planes", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4

    # Con filtro de entidad de OSDE (id=1)
    res_filter = await client.get("/api/v1/nomenclador/planes?entidad_financiadora_id=1", headers=auth_headers)
    assert res_filter.status_code == 200
    data_filter = res_filter.json()
    assert len(data_filter) == 2
    assert all(x["entidadFinanciadoraId"] == 1 for x in data_filter)


@pytest.mark.asyncio
async def test_nomenclador_unauthorized(client: AsyncClient):
    # Sin token
    res = await client.get("/api/v1/nomenclador/prestaciones")
    assert res.status_code == 401
