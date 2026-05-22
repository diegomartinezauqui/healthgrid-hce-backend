"""Tests para el flujo de episodios y actos médicos."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dev_auth import generate_dev_token, DevLoginRequest
from app.models.paciente import Paciente
from app.models.episodio import Episodio
from app.models.acto_medico import ActoMedico


@pytest.fixture
def auth_headers() -> dict:
    """Generar cabecera Authorization con token de dev (con todos los permisos necesarios)."""
    login_req = DevLoginRequest(
        sub=42,
        sede_id=3,
        permissions=[
            "hce:episodes:write",
            "hce:episodes:read",
            "hce:medical-acts:write",
            "hce:medical-acts:read",
        ]
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


@pytest.mark.asyncio
async def test_crear_episodio_y_acto_medico_flow(
    client: AsyncClient, db: AsyncSession, auth_headers: dict
):
    # 1. Crear un paciente en la base de datos de test
    paciente = Paciente(id_paciente=1001, datos_personales={"nombre": "Pepito"})
    db.add(paciente)
    await db.commit()

    # 2. Crear episodio médico (POST /patients/{id_paciente}/episodes)
    # Sin id_paciente ni id_medico_responsable en el body
    episodio_payload = {
        "tipo": "consulta-externa",
        "estado": "open",
        "id_sede": 5,
        "diagnostico_principal": "Neumonía leve"
    }
    
    response = await client.post(
        "/api/v1/patients/1001/episodes",
        json=episodio_payload,
        headers=auth_headers
    )
    assert response.status_code == 201
    ep_data = response.json()
    assert ep_data["id_paciente"] == 1001
    assert ep_data["tipo"] == "consulta-externa"
    assert ep_data["estado"] == "open"
    assert ep_data["id_sede"] == 5
    # El médico responsable debe coincidir con el 'sub' del token (42)
    assert ep_data["id_medico_responsable"] == 42
    assert ep_data["diagnostico_principal"] == "Neumonía leve"
    
    id_episodio = ep_data["id_episodio"]

    # 3. Crear acto médico sin id_profesional en el body (debe usar fallback del token)
    acto_payload_1 = {
        "codigo_nomenclador": "42.01.01",
        "descripcion": "Consulta médica general",
        "tipo": "consulta",
        "cantidad": 1
    }
    response_acto_1 = await client.post(
        f"/api/v1/patients/1001/episodes/{id_episodio}/medical-acts",
        json=acto_payload_1,
        headers=auth_headers
    )
    assert response_acto_1.status_code == 201
    acto_data_1 = response_acto_1.json()
    assert acto_data_1["id_episodio"] == id_episodio
    assert acto_data_1["codigo_nomenclador"] == "42.01.01"
    assert acto_data_1["tipo"] == "consulta"
    # El id_profesional debe ser por defecto el del token (42)
    assert acto_data_1["id_profesional"] == 42

    # 4. Crear acto médico especificando un profesional diferente
    acto_payload_2 = {
        "codigo_nomenclador": "99.01.01",
        "descripcion": "Intervención de especialista",
        "tipo": "procedimiento",
        "id_profesional": 999,
        "cantidad": 1
    }
    response_acto_2 = await client.post(
        f"/api/v1/patients/1001/episodes/{id_episodio}/medical-acts",
        json=acto_payload_2,
        headers=auth_headers
    )
    assert response_acto_2.status_code == 201
    acto_data_2 = response_acto_2.json()
    assert acto_data_2["id_episodio"] == id_episodio
    # El id_profesional especificado explícitamente no debe ser pisado
    assert acto_data_2["id_profesional"] == 999

    # 5. Obtener el detalle completo del episodio y verificar los actos
    response_detalle = await client.get(
        f"/api/v1/patients/1001/episodes/{id_episodio}",
        headers=auth_headers
    )
    assert response_detalle.status_code == 200
    det_data = response_detalle.json()
    assert det_data["id_episodio"] == id_episodio
    assert len(det_data["actos_medicos"]) == 2
    
    # Verificar orden/valores de los actos médicos cargados
    codigos = [a["codigo_nomenclador"] for a in det_data["actos_medicos"]]
    assert "42.01.01" in codigos
    assert "99.01.01" in codigos


@pytest.mark.asyncio
async def test_crear_episodio_default_sede(
    client: AsyncClient, db: AsyncSession, auth_headers: dict
):
    # Crear paciente
    paciente = Paciente(id_paciente=1002, datos_personales={"nombre": "Analia"})
    db.add(paciente)
    await db.commit()

    # Si no se envía id_sede en el body, se debe tomar del token del médico (sede_id=3 en auth_headers)
    episodio_payload = {
        "tipo": "guardia",
        "estado": "open",
        "diagnostico_principal": "Control"
    }
    
    response = await client.post(
        "/api/v1/patients/1002/episodes",
        json=episodio_payload,
        headers=auth_headers
    )
    assert response.status_code == 201
    ep_data = response.json()
    # Debe tomar la sede por defecto del token (3)
    assert ep_data["id_sede"] == 3
