import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.orden import Orden
from app.models.resultado import ResultadoLaboratorio, ResultadoImagen
from app.auth.dev_auth import generate_dev_token, DevLoginRequest
from common.enums.enums_orden import SubtipoEstudio


@pytest.fixture
def auth_headers() -> dict:
    login_req = DevLoginRequest(
        sub=101,  # ID del médico solicitante/firmante
        sede_id=1,
        permissions=[
            "hce:episodes:write",
            "hce:episodes:read",
            "hce:evoluciones:write",
            "hce:evoluciones:read",
            "hce:ordenes:write",
            "hce:ordenes:read",
            "hce:resultados:write",
            "hce:resultados:read",
        ],
    )
    token_res = generate_dev_token(login_req)
    return {"Authorization": f"Bearer {token_res.access_token}"}


@pytest.mark.asyncio
async def test_flujo_completo_ordenes_y_resultados(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente de prueba
    paciente = Paciente(id_paciente=10500, datos_personales={"nombre": "Juan Pérez"})
    db.add(paciente)
    await db.commit()

    # 2. Crear un episodio y una evolución
    res_ep = await client.post(
        "/api/v1/patients/10500/episodes",
        headers=auth_headers,
        json={"tipo": "consulta-externa"},
    )
    assert res_ep.status_code == 201
    id_episodio = res_ep.json()["id_episodio"]

    res_ev = await client.post(
        f"/api/v1/patients/10500/episodes/{id_episodio}/evoluciones",
        headers=auth_headers,
        json={"contenido": "Consulta inicial. Requiere resonancia e informe de laboratorio."},
    )
    assert res_ev.status_code == 201
    id_evolucion = res_ev.json()["id_evolucion"]

    # 3. Crear una Orden de Imagen (Módulo 5) con contexto clínico
    orden_img_payload = {
        "tipo_estudio": "Imagen",
        "descripcion_pedido": "RM de Cerebro con contraste",
        "prioridad": "Urgente",
        "id_episodio": id_episodio,
        "id_evolucion": id_evolucion,
    }
    res_orden_img = await client.post(
        "/api/v1/pacientes/10500/ordenes",
        headers=auth_headers,
        json=orden_img_payload,
    )
    assert res_orden_img.status_code == 201
    id_orden_img = res_orden_img.json()["id_orden"]

    # Validar persistencia de la orden de imagen
    q_orden_img = await db.execute(select(Orden).where(Orden.id_orden == id_orden_img))
    orden_img = q_orden_img.scalar_one()
    assert orden_img.tipo_estudio == "Imagen"
    assert orden_img.id_episodio == id_episodio
    assert orden_img.id_evolucion == id_evolucion
    assert orden_img.estado == "Pendiente"
    assert orden_img.id_medico_solicitante == 101

    # 4. Registrar resultado de Imagen (Módulo 5)
    resultado_img_payload = {
        "id_orden": id_orden_img,
        "id_paciente": 10500,
        "tipo_estudio": "Imagen",
        "id_profesional_firmante": "Dra. Gomez (Radiología)",
        "fecha_resultado": "2026-06-25T14:30:00Z",
        "informe_resumen": "RM de Cerebro: Sin hallazgos patológicos.",
        "id_externo_estudio": "550e8400-e29b-41d4-a716-446655440000",
        "subtipo": "RESONANCE",
        "link_imagen": "https://viewer.pacs.hospital/study/1234",
        "url_detalle": "https://api.imagenes.hospital/v1/estudios/1234/completo",
    }
    res_result_img = await client.post(
        "/api/v1/resultados",
        headers=auth_headers,
        json=resultado_img_payload,
    )
    assert res_result_img.status_code == 201

    # Verificar que el resultado de Imagen se guardó y la orden cambió a Finalizado
    await db.refresh(orden_img)
    assert orden_img.estado == "Finalizado"

    q_res_img = await db.execute(select(ResultadoImagen).where(ResultadoImagen.id_orden == id_orden_img))
    res_img = q_res_img.scalar_one()
    assert res_img.link_imagen == "https://viewer.pacs.hospital/study/1234"
    assert res_img.url_detalle == "https://api.imagenes.hospital/v1/estudios/1234/completo"
    assert res_img.informe_resumen == "RM de Cerebro: Sin hallazgos patológicos."
    assert res_img.subtipo == SubtipoEstudio.RESONANCIA

    # 5. Crear una Orden de Laboratorio (Módulo 4) con contexto clínico
    orden_lab_payload = {
        "tipo_estudio": "Laboratorio",
        "descripcion_pedido": "Hemograma completo",
        "prioridad": "Normal",
        "id_episodio": id_episodio,
        "id_evolucion": id_evolucion,
    }
    res_orden_lab = await client.post(
        "/api/v1/pacientes/10500/ordenes",
        headers=auth_headers,
        json=orden_lab_payload,
    )
    assert res_orden_lab.status_code == 201
    id_orden_lab = res_orden_lab.json()["id_orden"]

    # 6. Registrar resultado de Laboratorio (Módulo 4) mediante Webhook
    webhook_payload = {
        "evento": "laboratorio.resultado_listo",
        "version": "1.0",
        "id_evento": "uuid-test-1234",
        "fecha_ocurrencia": "2026-06-05T14:30:00Z",
        "orden": {
            "id_laboratorio": 42,
            "id_orden_hce": id_orden_lab,
            "descripcion": "Hemograma completo",
            "prioridad": "Routine",
            "fecha_solicitud": "2026-06-05T10:00:00Z",
            "fecha_resultado": "2026-06-05T14:30:00Z",
        },
        "paciente": {
            "id": 10500,
            "nombre": "Juan Pérez",
            "dni": "12345678",
        },
        "profesional_firmante": "Dra. García",
        "resumen": {
            "total_analitos": 1,
            "analitos_fuera_de_rango": 0,
            "hay_valores_criticos": False,
        },
        "analitos": [
            {
                "nombre": "Glucosa",
                "valor": 95.0,
                "unidad": "mg/dL",
                "rango_normal": {"min": 70.0, "max": 100.0},
                "fuera_de_rango": False,
                "es_critico": False,
                "observacion": None,
            }
        ],
    }

    res_webhook = await client.post(
        "/api/v1/webhook/laboratorio/resultado",
        json=webhook_payload,
    )
    assert res_webhook.status_code == 201

    # Verificar que el resultado de Laboratorio se guardó y la orden cambió a Finalizado
    q_orden_lab = await db.execute(select(Orden).where(Orden.id_orden == id_orden_lab))
    orden_lab = q_orden_lab.scalar_one()
    assert orden_lab.estado == "Finalizado"

    q_res_lab = await db.execute(select(ResultadoLaboratorio).where(ResultadoLaboratorio.id_orden == id_orden_lab))
    res_lab = q_res_lab.scalar_one()
    assert res_lab.id_externo_estudio == "42"
    assert res_lab.id_profesional_firmante == "Dra. García"
    assert res_lab.resumen_analitos["total_analitos"] == 1
    assert len(res_lab.analitos) == 1
    assert res_lab.analitos[0]["nombre"] == "Glucosa"
    assert res_lab.analitos[0]["valor"] == 95.0


@pytest.mark.asyncio
async def test_listar_ordenes_paciente(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    # 1. Crear un paciente de prueba
    paciente_id = 20500
    paciente = Paciente(id_paciente=paciente_id, datos_personales={"nombre": "María López"})
    db.add(paciente)
    await db.commit()

    # 2. Crear un par de órdenes
    orden1 = Orden(
        id_paciente=paciente_id,
        tipo_estudio="Laboratorio",
        descripcion_pedido="Rutina de sangre",
        prioridad="Normal",
        estado="Pendiente",
        id_medico_solicitante=101,
    )
    orden2 = Orden(
        id_paciente=paciente_id,
        tipo_estudio="Imagen",
        descripcion_pedido="Ecografía abdominal",
        prioridad="Urgente",
        estado="Pendiente",
        id_medico_solicitante=101,
        subtipo="ECOGRAFY",
    )
    db.add_all([orden1, orden2])
    await db.commit()

    # 3. Consultar las órdenes con autenticación exitosa
    response = await client.get(
        f"/api/v1/pacientes/{paciente_id}/ordenes",
        headers=auth_headers,
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["cantidad"] == 2
    
    ordenes_data = json_data["data"]
    # Al ordenar por fecha_creacion desc, orden2 o orden1 vendrán en cierto orden
    assert any(o["descripcion_pedido"] == "Rutina de sangre" and o["estado"] == "Pendiente" for o in ordenes_data)
    assert any(o["descripcion_pedido"] == "Ecografía abdominal" and o["subtipo"] == "ECOGRAFY" and o["estado"] == "Pendiente" for o in ordenes_data)

    # 4. Probar sin token de autenticación (401)
    response_unauth = await client.get(
        f"/api/v1/pacientes/{paciente_id}/ordenes"
    )
    assert response_unauth.status_code == 401

    # 5. Probar con token sin los permisos requeridos (403)
    login_req_no_perm = DevLoginRequest(
        sub=102,
        sede_id=1,
        permissions=["hce:pacientes:read"],  # No tiene hce:ordenes:read
    )
    token_res_no_perm = generate_dev_token(login_req_no_perm)
    bad_headers = {"Authorization": f"Bearer {token_res_no_perm.access_token}"}
    
    response_forbidden = await client.get(
        f"/api/v1/pacientes/{paciente_id}/ordenes",
        headers=bad_headers,
    )
    assert response_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_obtener_resultado_orden(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers: dict,
):
    from datetime import datetime

    # 1. Crear un paciente de prueba
    paciente_id = 30500
    paciente = Paciente(id_paciente=paciente_id, datos_personales={"nombre": "Carlos Gómez"})
    db.add(paciente)
    await db.commit()

    # 2. Crear una orden de Imagen
    orden_img = Orden(
        id_paciente=paciente_id,
        tipo_estudio="Imagen",
        descripcion_pedido="Radiografía de tórax",
        prioridad="Normal",
        estado="Finalizado",
        id_medico_solicitante=101,
        subtipo="RADIOLOGY",
    )
    db.add(orden_img)
    await db.commit()

    # 3. Crear el resultado de Imagen asociado
    resultado_img = ResultadoImagen(
        id_orden=orden_img.id_orden,
        id_paciente=paciente_id,
        id_profesional_firmante="Dr. Perez",
        fecha_resultado=datetime.utcnow(),
        titulo="Resultado RX Tórax",
        informe_resumen="Tórax normal, sin particularidades.",
        subtipo="RADIOLOGY",
        link_imagen="https://pacs.hospital/study/rx-123",
        url_detalle="https://api.imagenes.hospital/v1/estudios/rx-123",
    )
    db.add(resultado_img)
    await db.commit()

    # 4. Consultar resultado de la orden de Imagen (Éxito)
    response = await client.get(
        f"/api/v1/ordenes/{orden_img.id_orden}/resultado?tipo_estudio=Imagen",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tipo_estudio"] == "Imagen"
    assert data["id_orden"] == orden_img.id_orden
    assert data["titulo"] == "Resultado RX Tórax"
    assert data["link_imagen"] == "https://pacs.hospital/study/rx-123"

    # 5. Consultar resultado inexistente (404)
    response_404 = await client.get(
        f"/api/v1/ordenes/99999/resultado?tipo_estudio=Imagen",
        headers=auth_headers,
    )
    assert response_404.status_code == 404

    # 6. Probar sin token de autenticación (401)
    response_unauth = await client.get(
        f"/api/v1/ordenes/{orden_img.id_orden}/resultado?tipo_estudio=Imagen"
    )
    assert response_unauth.status_code == 401

    # 7. Probar con token sin los permisos requeridos (403)
    login_req_no_perm = DevLoginRequest(
        sub=102,
        sede_id=1,
        permissions=["hce:pacientes:read"],  # No tiene hce:resultados:read
    )
    token_res_no_perm = generate_dev_token(login_req_no_perm)
    bad_headers = {"Authorization": f"Bearer {token_res_no_perm.access_token}"}
    
    response_forbidden = await client.get(
        f"/api/v1/ordenes/{orden_img.id_orden}/resultado?tipo_estudio=Imagen",
        headers=bad_headers,
    )
    assert response_forbidden.status_code == 403


