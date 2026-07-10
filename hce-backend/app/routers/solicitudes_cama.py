"""
Endpoints de solicitudes de cama (internación / pase) — integración M6 (Camas).

HCE persiste la solicitud y su estado. El endpoint `resolver` simula la respuesta
de M6 (aceptada con cama / rechazada), que en producción llegaría por el callback
`POST /internacion/ingreso`.
"""

from fastapi import APIRouter, Depends, HTTPException, status

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
    _user=Depends(require_permission("hce:internacion:write")),
):
    try:
        solicitud = await solicitud_cama_service.crear_solicitud(db, id_paciente, id_episodio, body)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": str(e)})
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"error": "CONFLICT", "message": str(e)})
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
