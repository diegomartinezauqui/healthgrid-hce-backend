"""
Endpoints de episodios y actos médicos — Integración M7 (Facturación) y HCE.
Facturación consume para liquidación y HCE gestiona la atención médica.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.internacion import SolicitudInternacionRequest
from app.schemas.episodio import (
    ActoMedicoCreate,
    ActoMedicoListResponse,
    ActoMedicoSchema,
    EpisodioCreate,
    EpisodioDetalle,
    EpisodioListResponse,
    EpisodioResumen,
    EpisodioUpdate,
)
from app.services import episodio_service

router = APIRouter()


@router.get(
    "/patients/{id_paciente}/episodes",
    response_model=EpisodioListResponse,
    tags=["Atención Clínica — Episodios"],
    summary="Listar episodios médicos de un paciente",
    description=(
        "Permite a Facturación obtener el listado de episodios de un paciente "
        "para recopilar todos los actos médicos a liquidar."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def listar_episodios(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:read")),
    estado: Optional[str] = None,
    desde_fecha: Optional[date] = None,
    hasta_fecha: Optional[date] = None,
):
    try:
        episodios = await episodio_service.get_episodios_paciente(
            db, id_paciente, estado=estado, desde_fecha=desde_fecha, hasta_fecha=hasta_fecha
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )

    return EpisodioListResponse(
        id_paciente=id_paciente,
        total=len(episodios),
        episodios=[
            EpisodioResumen(
                id_episodio=ep.id_episodio,
                tipo=ep.tipo,
                estado=ep.estado,
                id_sede=ep.id_sede,
                fecha_apertura=ep.fecha_apertura,
                fecha_cierre=ep.fecha_cierre,
                id_medico_responsable=ep.id_medico_responsable,
            )
            for ep in episodios
        ],
    )


@router.post(
    "/patients/{id_paciente}/episodes",
    response_model=EpisodioDetalle,
    status_code=status.HTTP_201_CREATED,
    tags=["Atención Clínica — Episodios"],
    summary="Abrir un nuevo episodio médico",
    description="Permite registrar/abrir un nuevo episodio de atención (guardia, consulta externa, etc.) para el paciente.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def crear_episodio(
    id_paciente: int,
    body: EpisodioCreate,
    db: DbSession,
    user=Depends(require_permission("hce:episodes:write")),
):
    try:
        id_sede = body.id_sede or user.sede_id
        if not id_sede:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "UNPROCESSABLE_ENTITY", "message": "Debe especificar una sede (id_sede) en el body o tener una sede asociada a su usuario."},
            )
        episodio = await episodio_service.abrir_episodio(
            db, id_paciente, body, id_medico=user.sub, id_sede=id_sede
        )
        return EpisodioDetalle.model_validate(episodio)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}",
    response_model=EpisodioDetalle,
    tags=["Atención Clínica — Episodios"],
    summary="Obtener detalle completo de un episodio",
    description=(
        "Retorna el detalle de un episodio médico específico incluyendo todos "
        "los actos médicos registrados. Principal insumo para liquidación."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_episodio(
    id_paciente: int,
    id_episodio: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:read")),
):
    try:
        episodio = await episodio_service.get_episodio_detalle(db, id_paciente, id_episodio)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
    if not episodio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El recurso solicitado no fue encontrado."},
        )

    return EpisodioDetalle.model_validate(episodio)


@router.patch(
    "/patients/{id_paciente}/episodes/{id_episodio}",
    response_model=EpisodioDetalle,
    tags=["Atención Clínica — Episodios"],
    summary="Actualizar parcialmente un episodio médico",
    description="Permite realizar modificaciones parciales en el episodio o cerrarlo enviando estado='closed'.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def actualizar_episodio(
    id_paciente: int,
    id_episodio: int,
    body: EpisodioUpdate,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:write")),
):
    episodio = await episodio_service.actualizar_episodio(db, id_paciente, id_episodio, body)
    if not episodio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El recurso solicitado no fue encontrado."},
        )
    return EpisodioDetalle.model_validate(episodio)


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}/medical-acts",
    response_model=ActoMedicoListResponse,
    tags=["Atención Clínica — Actos Médicos"],
    summary="Listar actos médicos de un episodio",
    description=(
        "Lista todos los actos médicos registrados dentro de un episodio. "
        "Cada acto incluye el codigo_nomenclador para facturación."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def listar_actos_medicos(
    id_paciente: int,
    id_episodio: int,
    db: DbSession,
    _user=Depends(require_permission("hce:medical-acts:read")),
):
    actos = await episodio_service.get_actos_medicos_episodio(db, id_paciente, id_episodio)

    return ActoMedicoListResponse(
        id_episodio=id_episodio,
        total=len(actos),
        actos_medicos=[
            ActoMedicoSchema.model_validate(am)
            for am in actos
        ],
    )


@router.post(
    "/patients/{id_paciente}/episodes/{id_episodio}/medical-acts",
    response_model=ActoMedicoSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["Atención Clínica — Actos Médicos"],
    summary="Registrar un acto médico en un episodio",
    description="Permite registrar prestaciones/actos médicos dentro de un episodio activo de atención.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def crear_acto_medico(
    id_paciente: int,
    id_episodio: int,
    body: ActoMedicoCreate,
    db: DbSession,
    user=Depends(require_permission("hce:medical-acts:write")),
):
    try:
        acto = await episodio_service.registrar_acto_medico(
            db, id_paciente, id_episodio, body, id_profesional_default=user.sub
        )
        return ActoMedicoSchema.model_validate(acto)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "UNPROCESSABLE_ENTITY", "message": str(e)},
        )


@router.post(
    "/patients/{id_paciente}/episodes/{id_episodio}/solicitud-internacion",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Atención Clínica — Episodios"],
    summary="Solicitar internación del paciente (HCE → M6)",
    description=(
        "El médico indica la necesidad de internar a un paciente desde una evolución activa. "
        "HCE realiza una llamada REST sincrónica al Módulo 6 (Camas) para crear la solicitud "
        "de asignación de cama. M6 procesará la solicitud y, una vez asignada la cama, "
        "notificará a HCE mediante POST /internacion/ingreso. "
        "Permission claim requerido: `hce:internacion:write`."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
        403: {"model": ErrorResponse, "description": "Sin permiso requerido."},
        404: {"model": ErrorResponse, "description": "Episodio no encontrado."},
        422: {"model": ErrorResponse, "description": "Episodio cerrado o datos inválidos."},
        503: {"model": ErrorResponse, "description": "M6 no disponible."},
    },
)
async def solicitar_internacion(
    id_paciente: int,
    id_episodio: int,
    body: SolicitudInternacionRequest,
    request: Request,
    db: DbSession,
    user=Depends(require_permission("hce:internacion:write")),
):
    # Verificar que el episodio existe y pertenece al paciente
    episodio = await episodio_service.get_episodio_detalle(db, id_paciente, id_episodio)
    if not episodio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Episodio no encontrado."},
        )

    # Llamar a M6 para crear la solicitud de cama
    from app.services import m6_client
    # Extraer token del header Authorization para reenviar a M6
    auth_header = request.headers.get("Authorization")
    token = auth_header.replace("Bearer ", "") if auth_header else None

    try:
        resultado = await m6_client.solicitar_internacion(body, token=token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "SERVICE_UNAVAILABLE", "message": str(exc)},
        )

    return {
        "status": "accepted",
        "message": "Solicitud de internación enviada a M6 correctamente.",
        "m6_response": resultado,
    }
