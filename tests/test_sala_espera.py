import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.models.paciente import Paciente
from app.models.episodio import Episodio
from app.models.sala_espera import SalaEspera
from app.auth.dev_auth import generate_dev_token, DevLoginRequest
from app.kafka.handlers.presentismo_handler import handle_presentismo


@pytest.fixture
def auth_headers() -> dict:
    login_req = DevLoginRequest(
        sub=42,
        sede_id=3,
        permissions=[
            "hce:episodes:write",
            "hce:episodes:read",
        ],
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


@pytest.mark.asyncio
async def test_sala_espera_flow(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear pacientes en la base de datos de test
    p1 = Paciente(id_paciente=3001, datos_personales={"nombre": "Paciente Uno"})
    p2 = Paciente(id_paciente=3002, datos_personales={"nombre": "Paciente Dos"})
    db.add_all([p1, p2])
    await db.commit()

    # 1. Ingreso manual del Paciente Uno
    ingreso_payload_1 = {
        "id_paciente": 3001,
        "id_medico": 42,
        "id_sede": 3,
        "id_turno_m2": 50001
    }
    res_ingreso_1 = await client.post(
        "/api/v1/sala-espera/ingreso",
        json=ingreso_payload_1,
        headers=auth_headers
    )
    assert res_ingreso_1.status_code == 201
    data_1 = res_ingreso_1.json()
    assert data_1["estado"] == "Esperando"
    assert data_1["consultorio"] is None
    id_espera_1 = data_1["id_espera"]
    assert data_1["id_episodio"] is None
    assert data_1["motivo"] == "-"
    assert data_1["tipo_atencion"] == "consultorio"
    assert data_1["id_medico_triage"] is None
    assert data_1["paciente"] is not None
    assert data_1["paciente"]["id_paciente"] == 3001
    assert data_1["paciente"]["datos_personales"]["nombre"] == "Paciente Uno"


    # Verificar que NO se haya creado un episodio automático para Paciente Uno al ingresar
    result_ep_1 = await db.execute(
        select(Episodio).where(Episodio.id_paciente == 3001)
    )
    episodio_1 = result_ep_1.scalar_one_or_none()
    assert episodio_1 is None

    # 2. Ingreso manual del Paciente Dos
    ingreso_payload_2 = {
        "id_paciente": 3002,
        "id_medico": 42,
        "id_sede": 3,
        "id_turno_m2": 50002
    }
    res_ingreso_2 = await client.post(
        "/api/v1/sala-espera/ingreso",
        json=ingreso_payload_2,
        headers=auth_headers
    )
    assert res_ingreso_2.status_code == 201
    data_2 = res_ingreso_2.json()
    id_espera_2 = data_2["id_espera"]
    assert data_2["id_episodio"] is None

    # Llamar al nuevo endpoint de prioridad para simular triage asignando prioridad = 3
    # No enviamos motivo, por lo que debería mantener el motivo por defecto "-"
    res_prioridad = await client.patch(
        f"/api/v1/sala-espera/{id_espera_2}/prioridad",
        json={"prioridad": 3},
        headers=auth_headers
    )
    assert res_prioridad.status_code == 200
    assert res_prioridad.json()["prioridad"] == 3
    assert res_prioridad.json()["motivo"] == "-"
    assert res_prioridad.json()["id_medico_triage"] == 42

    # Actualizar prioridad nuevamente, esta vez enviando también un motivo de consulta
    res_prioridad_motivo = await client.patch(
        f"/api/v1/sala-espera/{id_espera_2}/prioridad",
        json={"prioridad": 4, "motivo": "Dolor fuerte de cabeza"},
        headers=auth_headers
    )
    assert res_prioridad_motivo.status_code == 200
    assert res_prioridad_motivo.json()["prioridad"] == 4
    assert res_prioridad_motivo.json()["motivo"] == "Dolor fuerte de cabeza"
    assert res_prioridad_motivo.json()["id_medico_triage"] == 42



    # 3. Consultar listado ordenado por prioridad (el Paciente Dos con prioridad 3 debería salir primero)
    res_list_prio = await client.get(
        "/api/v1/sala-espera?id_medico=42&ordenar_por=prioridad",
        headers=auth_headers
    )
    assert res_list_prio.status_code == 200
    lista_prio = res_list_prio.json()
    assert len(lista_prio) == 2
    assert lista_prio[0]["id_espera"] == id_espera_2  # Paciente Dos
    assert lista_prio[1]["id_espera"] == id_espera_1  # Paciente Uno

    # 4. Consultar listado ordenado por llegada (Paciente Uno primero)
    res_list_llegada = await client.get(
        "/api/v1/sala-espera?id_medico=42&ordenar_por=llegada",
        headers=auth_headers
    )
    assert res_list_llegada.status_code == 200
    lista_llegada = res_list_llegada.json()
    assert lista_llegada[0]["id_espera"] == id_espera_1
    assert lista_llegada[1]["id_espera"] == id_espera_2

    # 5. Llamar a Paciente Dos al Consultorio 204
    res_llamar = await client.patch(
        f"/api/v1/sala-espera/{id_espera_2}/llamar",
        json={"consultorio": 204},
        headers=auth_headers
    )
    assert res_llamar.status_code == 200
    data_llamado = res_llamar.json()
    assert data_llamado["estado"] == "Llamado"
    assert data_llamado["consultorio"] == 204

    # 6. Atender a Paciente Dos (se crea y asocia el episodio aquí)
    from unittest.mock import patch
    with patch("app.integrations.m2_client.iniciar_turno") as mock_iniciar:
        res_atender = await client.patch(
            f"/api/v1/sala-espera/{id_espera_2}/atender",
            headers=auth_headers
        )
    assert res_atender.status_code == 200
    mock_iniciar.assert_called_once_with(50002)
    data_atendido = res_atender.json()
    assert data_atendido["estado"] == "Atendido"
    assert data_atendido["id_episodio"] is not None

    # Verificar que se haya creado el episodio en la BD para el Paciente Dos
    result_ep_2 = await db.execute(
        select(Episodio).where(Episodio.id_paciente == 3002)
    )
    episodio_2 = result_ep_2.scalar_one_or_none()
    assert episodio_2 is not None
    assert episodio_2.tipo == "consulta-externa"
    assert episodio_2.id_episodio == data_atendido["id_episodio"]

    # 6.5 Finalizar atención a Paciente Dos
    with patch("app.integrations.m2_client.finalizar_turno") as mock_finalizar:
        res_finalizar = await client.patch(
            f"/api/v1/sala-espera/{id_espera_2}/finalizar",
            headers=auth_headers
        )
    assert res_finalizar.status_code == 200
    mock_finalizar.assert_called_once_with(50002)
    assert res_finalizar.json()["estado"] == "Finalizado"

    # 7. Marcar Ausente a Paciente Uno
    res_ausente = await client.patch(
        f"/api/v1/sala-espera/{id_espera_1}/ausente",
        headers=auth_headers
    )
    assert res_ausente.status_code == 200
    assert res_ausente.json()["estado"] == "Ausente"


@pytest.mark.asyncio
async def test_presentismo_kafka_integration(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear un paciente
    id_paciente = 3005
    paciente = Paciente(id_paciente=id_paciente, datos_personales={"nombre": "Paciente Kafka"})
    db.add(paciente)
    await db.commit()

    # 1. Simular la recepción de un evento Kafka de presentismo
    kafka_msg = {
        "id_turno_m2": 99001,
        "id_paciente": id_paciente,
        "id_profesional": "MP-42",
        "fecha_hora_llegada": datetime.now(timezone.utc).isoformat(),
        "motivo_turno": "Consulta de prueba"
    }
    
    await handle_presentismo(kafka_msg)

    # 2. Consultar a través del API si el paciente fue ingresado automáticamente en la sala de espera
    res_list = await client.get(
        "/api/v1/sala-espera?id_medico=42",
        headers=auth_headers
    )
    assert res_list.status_code == 200
    lista = res_list.json()
    
    registro_kafka = next((r for r in lista if r["id_paciente"] == id_paciente), None)
    assert registro_kafka is not None
    assert registro_kafka["estado"] == "Esperando"
    assert registro_kafka["id_turno_m2"] == 99001
    assert registro_kafka["motivo"] == "-"



@pytest.mark.asyncio
async def test_presentismo_webhook_integration(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear un paciente
    id_paciente = 3006
    paciente = Paciente(id_paciente=id_paciente, datos_personales={"nombre": "Paciente Webhook"})
    db.add(paciente)
    await db.commit()

    # 1. Simular la recepción de un webhook de presentismo enviando POST a /api/v1/sala-espera/ingreso
    payload = {
        "id_paciente": id_paciente,
        "id_profesional": 42,
        "id_sede": 3,
        "id_turno_m2": 77001,
        "fecha_turno": "2026-06-21T10:00:00Z",
        "fecha_llegada": "2026-06-21T09:45:00Z"
    }

    res = await client.post(
        "/api/v1/sala-espera/ingreso",
        json=payload,
        headers=auth_headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["estado"] == "Esperando"
    assert data["id_medico"] == 42
    assert data["id_turno_m2"] == 77001
    assert data["id_episodio"] is None
    assert data["motivo"] == "-"
    assert "2026-06-21T09:45:00" in data["fecha_llegada"]
    assert data["paciente"] is not None
    assert data["paciente"]["id_paciente"] == id_paciente
    assert data["paciente"]["datos_personales"]["nombre"] == "Paciente Webhook"


@pytest.mark.asyncio
async def test_atender_con_episodio_existente(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear un paciente
    id_paciente = 3010
    paciente = Paciente(id_paciente=id_paciente, datos_personales={"nombre": "Paciente Episodio Existente"})
    db.add(paciente)
    await db.commit()

    # 1. Crear un episodio médico manualmente para este paciente
    episodio_existente = Episodio(
        id_paciente=id_paciente,
        tipo="consulta-externa",
        estado="open",
        id_sede=3,
        id_medico_responsable=42,
        diagnostico_principal="Episodio previo abierto"
    )
    db.add(episodio_existente)
    await db.commit()
    await db.refresh(episodio_existente)

    # 2. Registrar ingreso a sala de espera
    payload_ingreso = {
        "id_paciente": id_paciente,
        "id_medico": 42,
        "id_sede": 3
    }
    res_ingreso = await client.post(
        "/api/v1/sala-espera/ingreso",
        json=payload_ingreso,
        headers=auth_headers
    )
    assert res_ingreso.status_code == 201
    data_ingreso = res_ingreso.json()
    id_espera = data_ingreso["id_espera"]
    assert data_ingreso["id_episodio"] is None

    # 3. Intentar atender asociando un episodio que no existe (debería dar 400)
    res_atender_error_inexistente = await client.patch(
        f"/api/v1/sala-espera/{id_espera}/atender",
        json={"id_episodio": 9999},
        headers=auth_headers
    )
    assert res_atender_error_inexistente.status_code == 400
    assert "no existe" in res_atender_error_inexistente.json()["detail"]["message"].lower()

    # 4. Intentar atender asociando un episodio de otro paciente (debería dar 400)
    # Crear otro paciente y su episodio
    paciente_otro = Paciente(id_paciente=3011, datos_personales={"nombre": "Otro Paciente"})
    db.add(paciente_otro)
    await db.commit()
    episodio_otro = Episodio(
        id_paciente=3011,
        tipo="consulta-externa",
        estado="open",
        id_sede=3,
        id_medico_responsable=42,
        diagnostico_principal="Episodio de otro paciente"
    )
    db.add(episodio_otro)
    await db.commit()
    await db.refresh(episodio_otro)

    res_atender_error_otro_paciente = await client.patch(
        f"/api/v1/sala-espera/{id_espera}/atender",
        json={"id_episodio": episodio_otro.id_episodio},
        headers=auth_headers
    )
    assert res_atender_error_otro_paciente.status_code == 400
    assert "no pertenece al paciente" in res_atender_error_otro_paciente.json()["detail"]["message"].lower()

    # 5. Atender asociando el episodio correcto
    res_atender_ok = await client.patch(
        f"/api/v1/sala-espera/{id_espera}/atender",
        json={"id_episodio": episodio_existente.id_episodio},
        headers=auth_headers
    )
    assert res_atender_ok.status_code == 200
    data_atendido = res_atender_ok.json()
    assert data_atendido["estado"] == "Atendido"
    assert data_atendido["id_episodio"] == episodio_existente.id_episodio


@pytest.mark.asyncio
async def test_paciente_endpoints(client: AsyncClient, db: AsyncSession, auth_headers: dict):
    # 0. Crear paciente
    p = Paciente(id_paciente=3050, datos_personales={"nombre": "Paciente Cache Test"})
    db.add(p)
    await db.commit()

    # 1. Consultar paciente por ID
    res = await client.get("/api/v1/pacientes/3050", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id_paciente"] == 3050
    assert data["datos_personales"]["nombre"] == "Paciente Cache Test"

    # 2. Consultar listado de pacientes
    res_list = await client.get("/api/v1/pacientes?limit=10", headers=auth_headers)
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert len(data_list) >= 1
    assert any(x["id_paciente"] == 3050 for x in data_list)



