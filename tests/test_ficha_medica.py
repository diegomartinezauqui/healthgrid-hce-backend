import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.paciente import Paciente
from app.models.ficha_medica import FichaMedica
from app.models.antecedente_paciente import AntecedentePaciente
from app.models.alerta_clinica import AlertaClinicaPaciente
from app.auth.dev_auth import generate_dev_token, DevLoginRequest


@pytest.fixture
def auth_headers() -> dict:
    login_req = DevLoginRequest(
        sub=42,
        sede_id=3,
        permissions=[
            "hce:ficha-medica:write",
            "hce:ficha-medica:read",
        ],
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


@pytest.mark.asyncio
async def test_crear_ficha_medica_completa(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear un paciente en la base de datos de test
    id_paciente = 2001
    paciente = Paciente(id_paciente=id_paciente, datos_personales={"nombre": "Paciente Ficha Completa"})
    db.add(paciente)
    await db.commit()

    # 1. Enviar petición para crear la ficha completa (ficha + antecedente + alerta)
    payload = {
        "ficha_medica": {
            "grupo_sanguineo": "0+",
            "peso_kg": 80.5,
            "altura_cm": 182.0,
            "observaciones_generales": "Ficha creada de forma atómica."
        },
        "antecedentes": [
            {
                "tipo": "Quirurgico",
                "descripcion": "Apendicectomía laparoscópica",
                "fecha_suceso": "2021-06-15",
                "observaciones": "Sin complicaciones postoperatorias."
            }
        ],
        "alertas_clinicas": [
            {
                "tipo": "Alergia",
                "severidad": "Severa",
                "descripcion": "Alergia a la Penicilina"
            }
        ]
    }

    response = await client.post(
        f"/api/v1/pacientes/{id_paciente}/ficha-completa",
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()

    # Verificar estructura de la respuesta
    assert "ficha_medica" in data
    assert data["ficha_medica"]["grupo_sanguineo"] == "0+"
    assert len(data["antecedentes"]) == 1
    assert data["antecedentes"][0]["descripcion"] == "Apendicectomía laparoscópica"
    assert len(data["alertas_clinicas"]) == 1
    assert data["alertas_clinicas"][0]["descripcion"] == "Alergia a la Penicilina"

    # 2. Verificar persistencia en base de datos
    # Ficha Medica
    result_ficha = await db.execute(select(FichaMedica).where(FichaMedica.id_paciente == id_paciente))
    ficha_db = result_ficha.scalar_one_or_none()
    assert ficha_db is not None
    assert ficha_db.grupo_sanguineo == "0+"

    # Antecedentes
    result_ant = await db.execute(select(AntecedentePaciente).where(AntecedentePaciente.id_paciente == id_paciente))
    antecedentes_db = result_ant.scalars().all()
    assert len(antecedentes_db) == 1
    assert antecedentes_db[0].descripcion == "Apendicectomía laparoscópica"

    # Alertas
    result_alt = await db.execute(select(AlertaClinicaPaciente).where(AlertaClinicaPaciente.id_paciente == id_paciente))
    alertas_db = result_alt.scalars().all()
    assert len(alertas_db) == 1
    assert alertas_db[0].descripcion == "Alergia a la Penicilina"


@pytest.mark.asyncio
async def test_crear_ficha_medica_completa_upsert(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear un paciente
    id_paciente = 2002
    paciente = Paciente(id_paciente=id_paciente, datos_personales={"nombre": "Paciente Duplicado"})
    db.add(paciente)
    await db.commit()

    payload = {
        "ficha_medica": {
            "grupo_sanguineo": "AB-",
            "peso_kg": 65.0,
            "altura_cm": 160.0,
            "observaciones_generales": "Primera ficha."
        },
        "antecedentes": [
            {
                "tipo": "Familiar",
                "descripcion": "Polen",
                "fecha_suceso": "2020-01-01"
            }
        ],
        "alertas_clinicas": [
            {
                "tipo": "Alergia",
                "severidad": "Leve",
                "descripcion": "Polen"
            }
        ],
        "dni": "99988877",
        "fecha_nacimiento": "1990-05-15",
        "genero": "M",
        "obra_social": "OSDE 310",
        "id_obra_social": 1,
        "numero_afiliado": "1234567890"
    }

    # Primera creación y sincronización demográfica
    response1 = await client.post(
        f"/api/v1/pacientes/{id_paciente}/ficha-completa",
        json=payload,
        headers=auth_headers
    )
    assert response1.status_code == 201
    
    # Verificar que los datos demográficos se guardaron en la caché del paciente
    await db.refresh(paciente)
    assert paciente.datos_personales["dni"] == "99988877"
    assert paciente.datos_personales["obra_social"] == "OSDE 310"

    # Verificar creación de cobertura médica
    from app.models.cobertura_medica import CoberturaMedica
    q_cob = await db.execute(select(CoberturaMedica).where(CoberturaMedica.id_paciente == id_paciente))
    cob = q_cob.scalar_one_or_none()
    assert cob is not None
    assert cob.id_obra_social == 1
    assert cob.numero_afiliado == "1234567890"

    # Segunda llamada (actualización/upsert)
    payload_update = {
        "ficha_medica": {
            "grupo_sanguineo": "A+",
            "peso_kg": 70.0,
            "altura_cm": 160.0,
            "observaciones_generales": "Ficha actualizada."
        },
        "antecedentes": [
            {
                "tipo": "Quirurgico",
                "descripcion": "Cesarea",
                "fecha_suceso": "2022-03-10"
            }
        ],
        "alertas_clinicas": [],
        "obra_social": "Swiss Medical",
        "id_obra_social": 2,
        "numero_afiliado": "0987654321"
    }

    response2 = await client.post(
        f"/api/v1/pacientes/{id_paciente}/ficha-completa",
        json=payload_update,
        headers=auth_headers
    )
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["ficha_medica"]["grupo_sanguineo"] == "A+"
    assert data2["ficha_medica"]["observaciones_generales"] == "Ficha actualizada."
    assert len(data2["antecedentes"]) == 1
    assert data2["antecedentes"][0]["descripcion"] == "Cesarea"
    assert len(data2["alertas_clinicas"]) == 0

    # Verificar actualización demográfica en paciente
    await db.refresh(paciente)
    assert paciente.datos_personales["obra_social"] == "Swiss Medical"
    # El DNI no debería haber cambiado porque no se envió en payload_update (None)
    assert paciente.datos_personales["dni"] == "99988877"

    # Verificar actualización de cobertura médica en cache local
    await db.refresh(cob)
    assert cob.id_obra_social == 2
    assert cob.numero_afiliado == "0987654321"


@pytest.mark.asyncio
async def test_crear_ficha_medica_completa_paciente_inexistente(client: AsyncClient, auth_headers: dict):
    payload = {
        "ficha_medica": {
            "grupo_sanguineo": "B+",
            "peso_kg": 70.0,
            "altura_cm": 170.0
        },
        "antecedentes": [],
        "alertas_clinicas": []
    }

    response = await client.post(
        "/api/v1/pacientes/99999/ficha-completa",
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "NOT_FOUND"
