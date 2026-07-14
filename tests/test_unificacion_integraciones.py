import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.episodio import Episodio
from app.models.resultado import ResultadoLaboratorio, ResultadoImagen
from app.models.orden import Orden
from app.models.solicitud_cama import SolicitudCama
from app.models.movimiento_internacion import MovimientoInternacion
from app.models.sala_espera import SalaEspera
from app.auth.dev_auth import generate_dev_token, DevLoginRequest
from common.enums.enums_orden import SubtipoEstudio, TipoEstudio
from common.enums.enums_episodio import TipoEpisodio, EstadoEpisodio


@pytest.fixture
def auth_headers() -> dict:
    login_req = DevLoginRequest(
        sub=101,
        sede_id=1,
        permissions=[
            "hce:episodes:write",
            "hce:episodes:read",
            "hce:ordenes:write",
            "hce:ordenes:read",
            "hce:resultados:write",
            "hce:resultados:read",
            "hce:internacion:write",
        ],
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


@pytest.mark.asyncio
async def test_webhook_presentismo_real_payload(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente de prueba
    paciente = Paciente(id_paciente=3365611, datos_personales={"nombre": "Juan Pérez"})
    db.add(paciente)
    await db.commit()

    # 2. Simular webhook de M2 (Turnos) con el payload real anidado
    m2_payload = {
        "reason": "El paciente hizo checkin",
        "appointment": {
            "id": 360,
            "starts_at": "2026-09-29 12:00:00",
            "checked_in_at": "2026-06-24 17:22:34",
        },
        "patient": {
            "id": 3365611,
        },
        "medic": {
            "id": 136156,
        },
        "disclaimer": "Notificación enviada por APPS 2 - Modulo 2 a través de Notifier",
    }

    res = await client.post(
        "/api/v1/webhook/turnos/presentismo",
        json=m2_payload,
    )
    assert res.status_code == 202

    # Verificar que el paciente fue ingresado a la sala de espera
    q_espera = await db.execute(select(SalaEspera).where(SalaEspera.id_paciente == 3365611))
    reg_espera = q_espera.scalar_one_or_none()
    assert reg_espera is not None
    assert reg_espera.id_turno_m2 == 360
    assert reg_espera.id_medico == 136156
    assert reg_espera.estado.value == "Esperando"


@pytest.mark.asyncio
async def test_flujo_solicitud_cama_m6(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente y un episodio de guardia de prueba
    paciente = Paciente(id_paciente=4455, datos_personales={"nombre": "Carlos Guardia"})
    db.add(paciente)
    await db.commit()

    res_ep = await client.post(
        "/api/v1/patients/4455/episodes",
        headers=auth_headers,
        json={"tipo": "guardia"},
    )
    assert res_ep.status_code == 201
    id_episodio = res_ep.json()["id_episodio"]

    # 2. Crear una solicitud de cama para el episodio (M6)
    solicitud_payload = {
        "tipo": "internacion",
        "prioridad": "Alta",
        "sector": "UTI",
        "motivo": "Insuficiencia respiratoria severa",
    }
    res_sol = await client.post(
        f"/api/v1/patients/4455/episodes/{id_episodio}/solicitudes-cama",
        headers=auth_headers,
        json=solicitud_payload,
    )
    assert res_sol.status_code == 201
    id_solicitud = res_sol.json()["id_solicitud"]

    # Verificar persistencia en estado pendiente
    q_sol = await db.execute(select(SolicitudCama).where(SolicitudCama.id_solicitud == id_solicitud))
    solicitud = q_sol.scalar_one()
    assert solicitud.estado == "pendiente"
    assert solicitud.prioridad == "Alta"

    # 3. Resolver la solicitud (M6 acepta y asigna cama)
    resolver_payload = {
        "decision": "aceptada",
        "cama": "Cama 104",
        "habitacion": "Habitacion 12",
    }
    res_res = await client.post(
        f"/api/v1/solicitudes-cama/{id_solicitud}/resolver",
        headers=auth_headers,
        json=resolver_payload,
    )
    assert res_res.status_code == 200

    # 4. Validar que el episodio cambió a Tipo Internación y que se registró el movimiento
    await db.refresh(solicitud)
    assert solicitud.estado == "aceptada"
    assert solicitud.cama == "Cama 104"

    q_ep = await db.execute(select(Episodio).where(Episodio.id_episodio == id_episodio))
    episodio = q_ep.scalar_one()
    assert episodio.tipo == TipoEpisodio.INTERNACION
    assert episodio.estado == EstadoEpisodio.OPEN

    q_mov = await db.execute(select(MovimientoInternacion).where(MovimientoInternacion.id_episodio == id_episodio))
    movimiento = q_mov.scalar_one_or_none()
    assert movimiento is not None
    assert movimiento.cama == "Cama 104"
    assert movimiento.habitacion == "Habitacion 12"


@pytest.mark.asyncio
async def test_webhook_m5_report_fallback(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear paciente
    paciente = Paciente(id_paciente=12345, datos_personales={"nombre": "Rosa M5"})
    db.add(paciente)
    await db.commit()

    # 2. Simular webhook de reporte de imagen finalizado sin informe (con fallback de mock_client)
    m5_webhook_payload = {
        "id_orden_hce": 9999,
        "report_id": "RPT-MOCK-777",
        "id_paciente": 12345,
        "titulo": "Resonancia Magnética de Rodilla",
        "informe": None,  # Forzar fallback a m5_client
        "profesional_firmante": None,
    }

    res = await client.post(
        "/api/v1/webhook/imagenes/reporte",
        headers=auth_headers,
        json=m5_webhook_payload,
    )
    assert res.status_code == 201

    # Verificar que el resultado de Imagen se guardó con PACS y fallback de informe
    q_res = await db.execute(select(ResultadoImagen).where(ResultadoImagen.id_externo_estudio == "RPT-MOCK-777"))
    resultado = q_res.scalar_one_or_none()
    assert resultado is not None
    # El subtipo fue inferido del título "Resonancia Magnética..."
    assert resultado.subtipo == SubtipoEstudio.RESONANCIA
    # El informe provino del mock client obtener_reporte
    assert "observations" in resultado.informe_resumen or "Campos pulmonares" in resultado.informe_resumen
    # Visor PACS generado
    assert resultado.link_imagen == "https://viewer.pacs.hospital/study/RPT-MOCK-777"


@pytest.mark.asyncio
async def test_crear_orden_laboratorio_m4_integration(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente de prueba
    paciente = Paciente(id_paciente=5566, datos_personales={"nombre": "Andrés Laboratorio"})
    db.add(paciente)
    await db.commit()

    # 2. Crear un episodio y una evolución
    res_ep = await client.post(
        "/api/v1/patients/5566/episodes",
        headers=auth_headers,
        json={"tipo": "consulta-externa"},
    )
    assert res_ep.status_code == 201
    id_episodio = res_ep.json()["id_episodio"]

    # 3. Crear una Orden de Laboratorio. Esto activará internamente la llamada al m4_client (mocked en tests).
    orden_lab_payload = {
        "tipo_estudio": "Laboratorio",
        "descripcion_pedido": "Perfil Renal completo",
        "prioridad": "Normal",
        "id_episodio": id_episodio,
    }
    res_orden = await client.post(
        "/api/v1/pacientes/5566/ordenes",
        headers=auth_headers,
        json=orden_lab_payload,
    )
    assert res_orden.status_code == 201
    id_orden = res_orden.json()["id_orden"]

    # 4. Probar directamente los métodos expuestos por el cliente HTTP de M4
    from app.integrations import m4_client
    
    # Test notificar_orden_laboratorio (modo mock)
    notif_res = await m4_client.notificar_orden_laboratorio(
        id_orden=id_orden,
        id_paciente=5566,
        paciente_nombre="Andrés Laboratorio",
        paciente_dni="12345678",
        paciente_edad=30,
        paciente_sexo="M",
        medico_id=101,
        estudio_ids=[1, 2],
        prioridad="Normal",
    )
    assert notif_res["status"] == "success"
    assert notif_res["mock"] is True
    assert notif_res["pacienteId"] == 5566
    assert notif_res["estudioIds"] == [1, 2]

    # Test obtener_estudios (modo mock)
    estudios_res = await m4_client.obtener_estudios()
    assert len(estudios_res) > 0
    assert estudios_res[0]["nombre"] == "Hemograma completo"

    # Test obtener_ordenes (modo mock)
    ordenes_res = await m4_client.obtener_ordenes({"pacienteId": 5566})
    assert ordenes_res["pacienteId"] == 5566


@pytest.mark.asyncio
async def test_crear_orden_laboratorio_endpoint(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente
    paciente = Paciente(id_paciente=6677, datos_personales={"nombre": "Laura Lab", "dni": "999999", "edad": 28, "sexo": "F"})
    db.add(paciente)
    await db.commit()

    # 2. POST /api/v1/pacientes/6677/ordenes/laboratorio
    payload = {
        "estudio_ids": [101, 102],
        "descripcion_pedido": "Muestras de sangre en ayunas",
        "prioridad": "Normal",
    }
    res = await client.post(
        "/api/v1/pacientes/6677/ordenes/laboratorio",
        headers=auth_headers,
        json=payload,
    )
    assert res.status_code == 201
    id_orden = res.json()["id_orden"]

    # 3. Verificar persistencia de la orden
    q = await db.execute(select(Orden).where(Orden.id_orden == id_orden))
    orden = q.scalar_one()
    assert orden.tipo_estudio == "Laboratorio"
    assert orden.estudio_ids == [101, 102]
    assert orden.descripcion_pedido == "Muestras de sangre en ayunas"


@pytest.mark.asyncio
async def test_crear_orden_imagenes_endpoint(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente
    paciente = Paciente(id_paciente=7788, datos_personales={"nombre": "Pedro Imagen", "dni": "888888", "edad": 42, "sexo": "M"})
    db.add(paciente)
    await db.commit()

    # 2. POST /api/v1/pacientes/7788/ordenes/imagenes
    payload = {
        "subtipo": "RADIOLOGY",
        "descripcion_pedido": "Placa de tórax AP",
        "prioridad": "Urgente",
    }
    res = await client.post(
        "/api/v1/pacientes/7788/ordenes/imagenes",
        headers=auth_headers,
        json=payload,
    )
    assert res.status_code == 201
    id_orden = res.json()["id_orden"]

    # 3. Verificar persistencia de la orden
    q = await db.execute(select(Orden).where(Orden.id_orden == id_orden))
    orden = q.scalar_one()
    assert orden.tipo_estudio == "Imagen"
    assert orden.subtipo == "RADIOLOGY"
    assert orden.descripcion_pedido == "Placa de tórax AP"


@pytest.mark.asyncio
async def test_webhook_presentismo_paciente_no_cacheado(
    client: AsyncClient,
    db: AsyncSession,
):
    from unittest.mock import patch

    # Enviar un webhook de presentismo para un paciente con id = 999999 que NO existe en base de datos.
    m2_payload = {
        "reason": "El paciente hizo checkin",
        "appointment": {
            "id": 880,
            "starts_at": "2026-09-29 12:00:00",
            "checked_in_at": "2026-06-24 17:22:34",
        },
        "patient": {
            "id": 999999,
        },
        "medic": {
            "id": 999888,
        },
        "disclaimer": "Notificación de integración",
    }

    # Mockeamos la sincronización para que devuelva None, forzando la creación del stub local de contingencia
    with patch("app.services.core_patient_sync.get_or_create_patient_from_core", return_value=None):
        res = await client.post(
            "/api/v1/webhook/turnos/presentismo",
            json=m2_payload,
        )
    assert res.status_code == 202

    # Verificar que el paciente fue creado dinámicamente como Stub
    q_paciente = await db.execute(select(Paciente).where(Paciente.id_paciente == 999999))
    paciente_stub = q_paciente.scalar_one_or_none()
    assert paciente_stub is not None
    assert "Paciente 999999" in paciente_stub.datos_personales["nombre"]
    assert paciente_stub.datos_personales["apellido"] == "Temporal HCE"

    # Verificar que el registro de sala de espera fue creado correctamente
    q_espera = await db.execute(select(SalaEspera).where(SalaEspera.id_paciente == 999999))
    reg_espera = q_espera.scalar_one_or_none()
    assert reg_espera is not None
    assert reg_espera.id_turno_m2 == 880
    assert reg_espera.id_medico == 999888



