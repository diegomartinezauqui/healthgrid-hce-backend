"""
Webhooks de ENTRADA — otros módulos notifican a HCE vía HTTP.
Unifica todas las integraciones de entrada (M2, M4, M5).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession
from app.schemas.resultado import ResultadoCreatedResponse, ResultadoEstudioRequest, ResultadoLaboratorioWebhook
from app.schemas.webhooks import M2CheckinWebhook, ReporteImagenWebhook
from app.services import resultado_service
from app.integrations import m5_client
from common.enums.enums_orden import TipoEstudio, SubtipoEstudio

router = APIRouter(prefix="/webhook", tags=["Webhooks de integración (entrada)"])


@router.post(
    "/turnos/presentismo",
    status_code=status.HTTP_202_ACCEPTED,
    summary="M2 notifica check-in de paciente (webhook)",
    description="Recibe el presentismo real del Módulo 2, lo adapta e ingresa al paciente en la sala de espera.",
)
async def webhook_presentismo(body: M2CheckinWebhook):
    # Adaptar estructura anidada de M2 a la estructura plana esperada por el handler
    presentismo_interno = {
        "id_turno_m2": body.appointment.id,
        "id_paciente": body.patient.id,
        "id_profesional": str(body.medic.id),
        "fecha_hora_llegada": body.appointment.checked_in_at,
        "fecha_turno": body.appointment.starts_at,
        "motivo_turno": body.reason,
    }

    from app.kafka.handlers.presentismo_handler import handle_presentismo
    await handle_presentismo(presentismo_interno)
    return {"status": "accepted", "message": "Presentismo procesado, paciente en sala de espera."}


@router.post(
    "/laboratorio/resultado",
    response_model=ResultadoCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Webhook para registrar resultados de Laboratorio (Módulo 4)",
    description="Recibe el webhook de laboratorio.resultado_listo y lo guarda con analitos enriquecidos.",
)
async def webhook_resultado_laboratorio(body: ResultadoLaboratorioWebhook, db: DbSession):
    await resultado_service.registrar_resultado_laboratorio(db, body)
    return ResultadoCreatedResponse(
        status="success",
        message="Resultado de laboratorio vinculado correctamente a la Historia Clínica.",
    )


@router.post(
    "/imagenes/reporte",
    response_model=ResultadoCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="M5 notifica un reporte de imagen finalizado (webhook)",
    description=(
        "Registra los detalles del reporte de imágenes. Si el informe o profesional vienen vacíos, "
        "los recupera dinámicamente llamando al API del Módulo 5."
    ),
)
async def webhook_reporte_imagen(body: ReporteImagenWebhook, db: DbSession):
    informe = body.informe
    titulo = body.titulo
    profesional = body.profesional_firmante
    fecha = body.fecha_resultado or datetime.utcnow()

    # Si el informe viene vacío y tenemos report_id, consultamos a M5
    if not informe and body.report_id:
        try:
            detalle = await m5_client.obtener_reporte(body.report_id)
            # En M5 el reporte tiene observations y conclusion
            obs = detalle.get("observations") or ""
            concl = detalle.get("conclusion") or ""
            informe = f"{obs}\nConclusión: {concl}".strip() or "Reporte sin texto adicional."
            titulo = titulo or detalle.get("title") or detalle.get("titulo")
            profesional = profesional or detalle.get("doctorName") or detalle.get("profesional_firmante")
            if detalle.get("date"):
                try:
                    fecha = datetime.fromisoformat(detalle["date"])
                except Exception:
                    pass
        except Exception as e:
            informe = f"Error al recuperar detalle de M5: {e}"

    # Resolver el subtipo (ej: ecografía, tomografía)
    subtipo = None
    if titulo:
        titulo_upper = titulo.upper()
        if "RESONAN" in titulo_upper or "RM" in titulo_upper:
            subtipo = SubtipoEstudio.RESONANCIA
        elif "TOMOGRAF" in titulo_upper or "TC" in titulo_upper or "TAC" in titulo_upper:
            subtipo = SubtipoEstudio.TOMOGRAFIA
        elif "ECOGRAF" in titulo_upper or "ECO" in titulo_upper:
            subtipo = SubtipoEstudio.ECOGRAFIA
        elif "RADIOGRAF" in titulo_upper or "RX" in titulo_upper:
            subtipo = SubtipoEstudio.RADIOLOGIA
        elif "MAMOGRAF" in titulo_upper:
            subtipo = SubtipoEstudio.MAMOGRAFIA
        elif "DENSITOMETR" in titulo_upper:
            subtipo = SubtipoEstudio.DENSITOMETRIA
        elif "DOPPLER" in titulo_upper:
            subtipo = SubtipoEstudio.ECODOPPLER
        elif "ENDOSCOP" in titulo_upper:
            subtipo = SubtipoEstudio.ENDOSCOPIA

    # Construir URLs dinámicas para el visor PACS e informes de M5
    link_imagen = f"https://viewer.pacs.hospital/study/{body.report_id}" if body.report_id else None
    url_detalle = f"{m5_client.settings.M5_BASE_URL}/v1/webhook/reportById?reportId={body.report_id}" if body.report_id else None

    request_data = ResultadoEstudioRequest(
        id_orden=body.id_orden_hce,
        id_paciente=body.id_paciente,
        tipo_estudio=TipoEstudio.IMAGEN,
        id_profesional_firmante=profesional or "Diagnóstico por Imagen",
        fecha_resultado=fecha,
        informe_resumen=informe or f"Estudio de imagen: {titulo or ''}",
        id_externo_estudio=body.report_id,
        subtipo=subtipo,
        link_imagen=link_imagen,
        url_detalle=url_detalle,
    )

    await resultado_service.registrar_resultado(db, request_data)
    return ResultadoCreatedResponse(
        status="success",
        message="Reporte de imagen vinculado correctamente a la Historia Clínica.",
    )


from fastapi import HTTPException
from app.schemas.webhooks import M6ResolucionWebhook
from app.schemas.solicitud_cama import SolicitudCamaResolver
from app.services import solicitud_cama_service
import re

@router.post(
    "/camas/resolucion",
    status_code=status.HTTP_200_OK,
    summary="Webhook para recibir resoluciones de camas de M6",
    description="Recibe el webhook de M6 cuando una solicitud de cama es resuelta (aprobada/rechazada)."
)
async def webhook_resolucion_cama(body: M6ResolucionWebhook, db: DbSession):
    # Extraer el ID numérico de la solicitud
    solicitud_id_raw = body.solicitud_hce_id
    if isinstance(solicitud_id_raw, str):
        digits = re.findall(r'\d+', solicitud_id_raw)
        id_solicitud = int(digits[0]) if digits else None
    else:
        id_solicitud = solicitud_id_raw

    if not id_solicitud:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_ID", "message": "No se pudo extraer el id de solicitud numérico."}
        )

    # Mapear decisión
    decision_raw = (body.decision or "").lower()
    decision = "aceptada" if "aprobada" in decision_raw or "aceptada" in decision_raw else "rechazada"

    resolver_body = SolicitudCamaResolver(
        decision=decision,
        cama=body.cama,
        habitacion=body.habitacion,
        motivo_rechazo=body.motivo_rechazo,
    )

    try:
        await solicitud_cama_service.resolver_solicitud(db, id_solicitud, resolver_body)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(exc)}
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BAD_REQUEST", "message": str(exc)}
        )

    return {"status": "success", "message": f"Solicitud {id_solicitud} resuelta como {decision}."}
