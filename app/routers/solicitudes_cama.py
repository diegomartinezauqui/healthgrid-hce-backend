"""
Endpoints de solicitudes de cama (internación / pase) — integración M6 (Camas).

HCE persiste la solicitud y su estado. El endpoint `resolver` simula la respuesta
de M6 (aceptada con cama / rechazada), que en producción llegaría por el callback
`POST /internacion/ingreso`.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

import logging

logger = logging.getLogger(__name__)

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.solicitud_cama import (
    CamaActual,
    SolicitudCamaCreate,
    SolicitudCamaListResponse,
    SolicitudCamaResolver,
    SolicitudCamaSchema,
)
from app.services import solicitud_cama_service

router = APIRouter(tags=["Solicitudes de cama (M6)"])


@router.post(
    "/patients/{id_paciente}/episodes/{id_episodio}/solicitudes-cama",
    response_model=SolicitudCamaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear solicitud de internación o pase de cama",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def crear_solicitud_cama(
    id_paciente: int,
    id_episodio: int,
    body: SolicitudCamaCreate,
    db: DbSession,
    request: Request,
    _user=Depends(require_permission("hce:internacion:write")),
):
    try:
        solicitud = await solicitud_cama_service.crear_solicitud(db, id_paciente, id_episodio, body)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": str(e)})
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"error": "CONFLICT", "message": str(e)})

    # Notificar a M6 (Camas) — utiliza modo asíncrono si ENABLE_CORE_BUS=true
    from app.services import m6_client
    from app.schemas.internacion import SolicitudInternacionRequest
    from sqlalchemy import select
    from app.models.evolucion import Evolucion

    try:
        q_ev = await db.execute(
            select(Evolucion.id_evolucion, Evolucion.id_profesional)
            .where(Evolucion.id_episodio == id_episodio)
            .order_by(Evolucion.fecha.desc())
        )
        row = q_ev.first()
        id_ev, id_prof = row if row else (0, 0)

        # Normalizar sector
        sect_str = str(body.sector or "").lower()
        if "uti" in sect_str:
            sector_val = "UTI"
        elif "guardia" in sect_str:
            sector_val = "Guardia_Observacion"
        else:
            sector_val = "Sala_Comun"

        # Mapear prioridad
        prio_str = str(body.prioridad or "").lower()
        if prio_str == "alta":
            prio_val = "Alta"
        elif prio_str == "baja":
            prio_val = "Baja"
        else:
            prio_val = "Media"

        sol_request = SolicitudInternacionRequest(
            id_paciente=id_paciente,
            id_episodio=id_episodio,
            id_evolucion_origen=id_ev,
            prioridad=prio_val,
            sector_solicitado=sector_val,
            diagnostico_principal=body.motivo or "Solicitud de cama desde pestaña",
            observaciones=body.motivo,
            id_solicitud=solicitud.id_solicitud,
            tipo=body.tipo,
            medico_solicitante_id=id_prof or 0
        )

        auth_header = request.headers.get("Authorization")
        token = auth_header.replace("Bearer ", "") if auth_header else None
        await m6_client.solicitar_internacion(sol_request, token=token)
    except Exception as exc:
        logger.error("❌ [M6] No se pudo notificar la solicitud de internación a M6: %s", exc)

    return SolicitudCamaSchema.model_validate(solicitud)


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}/solicitudes-cama",
    response_model=SolicitudCamaListResponse,
    summary="Listar solicitudes de cama del episodio + cama actual",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def listar_solicitudes_cama(
    id_paciente: int,
    id_episodio: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:read")),
):
    solicitudes = await solicitud_cama_service.listar_por_episodio(db, id_episodio)
    movimiento = await solicitud_cama_service.get_cama_actual(db, id_episodio)

    cama_actual = None
    if movimiento is not None:
        cama_actual = CamaActual(
            sector=movimiento.sector,
            habitacion=movimiento.habitacion,
            cama=movimiento.cama,
            fecha_ingreso=movimiento.fecha_ingreso,
        )

    return SolicitudCamaListResponse(
        solicitudes=[SolicitudCamaSchema.model_validate(s) for s in solicitudes],
        cama_actual=cama_actual,
        internado=cama_actual is not None,
    )


@router.post(
    "/solicitudes-cama/{id_solicitud}/resolver",
    response_model=SolicitudCamaSchema,
    summary="Simular respuesta de M6 (aceptar con cama / rechazar)",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def resolver_solicitud_cama(
    id_solicitud: int,
    body: SolicitudCamaResolver,
    db: DbSession,
    _user=Depends(require_permission("hce:internacion:write")),
):
    try:
        solicitud = await solicitud_cama_service.resolver_solicitud(db, id_solicitud, body)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": str(e)})
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "UNPROCESSABLE", "message": str(e)})
    return SolicitudCamaSchema.model_validate(solicitud)


@router.post(
    "/solicitudes-cama/{id_solicitud}/cancelar",
    response_model=SolicitudCamaSchema,
    summary="Cancelar una solicitud de cama pendiente",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def cancelar_solicitud_cama(
    id_solicitud: int,
    db: DbSession,
    _user=Depends(require_permission("hce:internacion:write")),
):
    try:
        solicitud = await solicitud_cama_service.cancelar_solicitud(db, id_solicitud)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": str(e)})
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "UNPROCESSABLE", "message": str(e)})
    return SolicitudCamaSchema.model_validate(solicitud)


from app.schemas.webhooks import M6ResolucionWebhook
import re

@router.post(
    "/hce/solicitudes/{solicitud_id}/resultado",
    response_model=SolicitudCamaSchema,
    summary="Recibir resolución de solicitud de cama (REST callback de M6)",
    description="Recibe la resolución (aprobada/rechazada) desde M6 de forma directa vía HTTP REST."
)
async def webhook_resolucion_cama_legacy(
    solicitud_id: str,
    body: M6ResolucionWebhook,
    db: DbSession,
):
    logger.warning("📥 [M6 Legacy REST] Recibida resolución para %s: %s", solicitud_id, body.model_dump())
    
    # Extraer ID numérico
    digits = re.findall(r'\d+', solicitud_id)
    id_solicitud = int(digits[0]) if digits else None

    if not id_solicitud:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_ID", "message": "No se pudo extraer el id numérico de la URL."}
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
        solicitud = await solicitud_cama_service.resolver_solicitud(db, id_solicitud, resolver_body)
        await db.commit()
        logger.warning("✅ [M6 Legacy REST] Solicitud %s resuelta como %s", id_solicitud, decision)
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

    return SolicitudCamaSchema.model_validate(solicitud)

