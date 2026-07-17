import pytest
from httpx import AsyncClient

from app.models.receta import Receta
from app.models.item_receta import ItemReceta
from app.auth.dev_auth import generate_dev_token, DevLoginRequest


@pytest.fixture
def auth_headers() -> dict:
    login_req = DevLoginRequest(
        sub=42,
        sede_id=3,
        permissions=[
            "hce:episodes:write",
            "hce:episodes:read",
            "hce:evoluciones:write",
            "hce:evoluciones:read",
            "hce:recetas:write",
            "hce:recetas:read",
        ],
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


from sqlalchemy.ext.asyncio import AsyncSession
from app.models.paciente import Paciente


@pytest.mark.asyncio
async def test_crear_receta_master_detail(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    """Test para crear una receta con múltiples medicamentos (ítems)."""
    
    # 0. Crear un paciente en la base de datos de test
    paciente = Paciente(id_paciente=1001, datos_personales={"nombre": "Prueba"})
    db.add(paciente)
    await db.commit()

    # 1. Crear un episodio
    res_ep = await client.post(
        "/api/v1/patients/1001/episodes",
        headers=auth_headers,
        json={"tipo": "consulta-externa"},
    )
    assert res_ep.status_code == 201
    id_episodio = res_ep.json()["id_episodio"]

    # 2. Crear una evolución
    res_ev = await client.post(
        f"/api/v1/patients/1001/episodes/{id_episodio}/evoluciones",
        headers=auth_headers,
        json={"contenido": "Paciente presenta infección. Se recetan antibióticos."},
    )
    assert res_ev.status_code == 201
    id_evolucion = res_ev.json()["id_evolucion"]

    # 3. Crear Receta con múltiples ítems
    receta_payload = {
        "items": [
            {
                "medicamento": "Amoxicilina 500mg",
                "indicaciones": "1 comprimido cada 8 horas",
                "cantidad": 1
            },
            {
                "medicamento": "Ibuprofeno 400mg",
                "indicaciones": "1 comprimido cada 8 horas si hay dolor",
                "cantidad": 2
            }
        ]
    }
    
    res_receta = await client.post(
        f"/api/v1/patients/1001/episodes/{id_episodio}/evoluciones/{id_evolucion}/recetas",
        headers=auth_headers,
        json=receta_payload,
    )
    
    if res_receta.status_code != 201:
        print(f"ERROR RECETA: {res_receta.json()}")
    assert res_receta.status_code == 201
    data = res_receta.json()
    assert "id_receta" in data
    assert "fecha_creacion" in data
    assert data["fecha_creacion"] is not None
    assert len(data["items"]) == 2
    assert data["items"][0]["medicamento"] == "Amoxicilina 500mg"
    assert data["items"][1]["medicamento"] == "Ibuprofeno 400mg"
    assert data["items"][1]["cantidad"] == 2
    
    id_receta = data["id_receta"]
    
    # 4. Validar que el endpoint GET /recetas (M3 Farmacia) la devuelve estructurada
    res_get = await client.get("/api/v1/recetas", headers=auth_headers)
    assert res_get.status_code == 200
    recetas_list = res_get.json()["data"]
    
    receta_farmacia = next((r for r in recetas_list if r["id_receta"] == id_receta), None)
    assert receta_farmacia is not None
    assert "fecha_creacion" in receta_farmacia
    assert len(receta_farmacia["items"]) == 2

    # 5. Dispensar la receta a través del endpoint PATCH /recetas/{id_receta}/dispensar
    res_dispensar = await client.patch(
        f"/api/v1/recetas/{id_receta}/dispensar",
        headers=auth_headers
    )
    assert res_dispensar.status_code == 200
    data_dispensada = res_dispensar.json()
    assert data_dispensada["estado"] == "Dispensada"

    # 6. Validar que al hacer un GET individual o listado el estado persistido sea "Dispensada"
    res_get_single = await client.get(
        f"/api/v1/recetas/{id_receta}",
        headers=auth_headers
    )
    assert res_get_single.status_code == 200
    assert res_get_single.json()["estado"] == "Dispensada"

    # 7. Intentar dispensar la receta de nuevo (ahora que ya está "Dispensada", estado no es "Activa")
    res_dispensar_again = await client.patch(
        f"/api/v1/recetas/{id_receta}/dispensar",
        headers=auth_headers
    )
    assert res_dispensar_again.status_code == 422
    assert res_dispensar_again.json()["detail"]["error"] == "UNPROCESSABLE_ENTITY"


@pytest.mark.asyncio
async def test_listar_medicamentos(client: AsyncClient, auth_headers: dict):
    # 1. Obtener listado completo de medicamentos sin filtros
    res = await client.get("/api/v1/medicamentos", headers=auth_headers)
    assert res.status_code == 200
    meds = res.json()
    assert len(meds) >= 15
    assert any(m["nombre"] == "Ibuprofeno 600mg" for m in meds)

    # 2. Filtrar medicamentos por consulta "amoxi"
    res_filter = await client.get("/api/v1/medicamentos?q=amoxi", headers=auth_headers)
    assert res_filter.status_code == 200
    filtered_meds = res_filter.json()
    assert len(filtered_meds) == 1
    assert filtered_meds[0]["nombre"] == "Amoxicilina 500mg"


@pytest.mark.asyncio
async def test_listar_recetas_filtrado_por_episodio(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear un paciente de prueba
    id_paciente = 1002
    paciente = Paciente(id_paciente=id_paciente, datos_personales={"nombre": "Episodio Filter"})
    db.add(paciente)
    await db.commit()

    # 1. Crear Episodio A y Evolución A
    res_ep_a = await client.post(f"/api/v1/patients/{id_paciente}/episodes", headers=auth_headers, json={"tipo": "consulta-externa"})
    id_episodio_a = res_ep_a.json()["id_episodio"]
    res_ev_a = await client.post(f"/api/v1/patients/{id_paciente}/episodes/{id_episodio_a}/evoluciones", headers=auth_headers, json={"contenido": "A"})
    id_evolucion_a = res_ev_a.json()["id_evolucion"]

    # 2. Crear Episodio B y Evolución B
    res_ep_b = await client.post(f"/api/v1/patients/{id_paciente}/episodes", headers=auth_headers, json={"tipo": "consulta-externa"})
    id_episodio_b = res_ep_b.json()["id_episodio"]
    res_ev_b = await client.post(f"/api/v1/patients/{id_paciente}/episodes/{id_episodio_b}/evoluciones", headers=auth_headers, json={"contenido": "B"})
    id_evolucion_b = res_ev_b.json()["id_evolucion"]

    # 3. Crear receta en Episodio A
    await client.post(
        f"/api/v1/patients/{id_paciente}/episodes/{id_episodio_a}/evoluciones/{id_evolucion_a}/recetas",
        headers=auth_headers,
        json={"items": [{"medicamento": "M1", "cantidad": 1}]}
    )

    # 4. Crear receta en Episodio B
    await client.post(
        f"/api/v1/patients/{id_paciente}/episodes/{id_episodio_b}/evoluciones/{id_evolucion_b}/recetas",
        headers=auth_headers,
        json={"items": [{"medicamento": "M2", "cantidad": 1}]}
    )

    # 5. Listar recetas filtradas por Episodio A
    res_get_a = await client.get(f"/api/v1/recetas?id_episodio={id_episodio_a}", headers=auth_headers)
    assert res_get_a.status_code == 200
    recetas_a = res_get_a.json()["data"]
    assert len(recetas_a) == 1
    assert recetas_a[0]["id_evolucion"] == id_evolucion_a
    assert recetas_a[0]["items"][0]["medicamento"] == "M1"

    # 6. Listar recetas filtradas por Episodio B
    res_get_b = await client.get(f"/api/v1/recetas?id_episodio={id_episodio_b}", headers=auth_headers)
    assert res_get_b.status_code == 200
    recetas_b = res_get_b.json()["data"]
    assert len(recetas_b) == 1
    assert recetas_b[0]["id_evolucion"] == id_evolucion_b
    assert recetas_b[0]["items"][0]["medicamento"] == "M2"


