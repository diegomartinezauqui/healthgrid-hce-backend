"""
Endpoints de evoluciones médicas — Integración M7 (Facturación) y HCE.
Manejo de notas de evolución dentro de un episodio.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.evolucion import (
    EvolucionCreate,
    EvolucionListResponse,
    EvolucionSchema,
    EvolucionUpdate,
)
from app.services import evolucion_service

router = APIRouter()


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}/evoluciones",
    response_model=EvolucionListResponse,
    tags=["Atención Clínica — Evoluciones"],
    summary="Listar evoluciones médicas de un episodio",
    description=(
        "Lista todas las notas de evolución registradas dentro de un episodio, "
        "ordenadas cronológicamente."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def listar_evoluciones(
    id_paciente: int,
    id_episodio: int,
    db: DbSession,
    _user=Depends(require_permission("hce:evoluciones:read")),
):
    try:
        evoluciones = await evolucion_service.get_evoluciones_episodio(
            db, id_paciente, id_episodio
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )

    return EvolucionListResponse(
        id_episodio=id_episodio,
        total=len(evoluciones),
        evoluciones=[
            EvolucionSchema.model_validate(ev) for ev in evoluciones
        ],
    )


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}/evoluciones/{id_evolucion}",
    response_model=EvolucionSchema,
    tags=["Atención Clínica — Evoluciones"],
    summary="Obtener detalle de una evolución médica",
    description="Retorna el contenido completo de una nota de evolución específica.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_evolucion(
    id_paciente: int,
    id_episodio: int,
    id_evolucion: int,
    db: DbSession,
    _user=Depends(require_permission("hce:evoluciones:read")),
):
    try:
        evolucion = await evolucion_service.get_evolucion_detalle(
            db, id_paciente, id_episodio, id_evolucion
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )

    if not evolucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "La evolución solicitada no fue encontrada."},
        )

    return EvolucionSchema.model_validate(evolucion)


@router.post(
    "/patients/{id_paciente}/episodes/{id_episodio}/evoluciones",
    response_model=EvolucionSchema,
    status_code=status.HTTP_201_CREATED,
    tags=["Atención Clínica — Evoluciones"],
    summary="Registrar una evolución médica en un episodio",
    description=(
        "Permite registrar una nota de evolución clínica dentro de un episodio activo. "
        "El profesional autor se obtiene automáticamente del token JWT."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def crear_evolucion(
    id_paciente: int,
    id_episodio: int,
    body: EvolucionCreate,
    db: DbSession,
    user=Depends(require_permission("hce:evoluciones:write")),
):
    try:
        evolucion = await evolucion_service.registrar_evolucion(
            db, id_paciente, id_episodio, body, id_profesional=user.sub
        )
        return EvolucionSchema.model_validate(evolucion)
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


@router.patch(
    "/patients/{id_paciente}/episodes/{id_episodio}/evoluciones/{id_evolucion}",
    response_model=EvolucionSchema,
    tags=["Atención Clínica — Evoluciones"],
    summary="Actualizar parcialmente una evolución médica",
    description="Permite corregir el contenido de una nota de evolución existente.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def actualizar_evolucion(
    id_paciente: int,
    id_episodio: int,
    id_evolucion: int,
    body: EvolucionUpdate,
    db: DbSession,
    _user=Depends(require_permission("hce:evoluciones:write")),
):
    try:
        evolucion = await evolucion_service.actualizar_evolucion(
            db, id_paciente, id_episodio, id_evolucion, body
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )

    if not evolucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "La evolución solicitada no fue encontrada."},
        )

    return EvolucionSchema.model_validate(evolucion)
