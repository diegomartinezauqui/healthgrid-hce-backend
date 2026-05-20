"""
Endpoints de alertas clínicas del paciente.
CRUD completo para registro y resolución de consideraciones de seguridad.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.alerta import AlertaCreate, AlertaSchema, AlertaUpdate
from app.schemas.common import ErrorResponse
from app.services import alerta_service

router = APIRouter()


@router.get(
    "/pacientes/{id_paciente}/alertas",
    response_model=list[AlertaSchema],
    summary="Listar alertas clínicas de un paciente",
    description="Retorna todas las alertas del paciente (Activas y Resueltas).",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
    },
)
async def listar_alertas(
    id_paciente: int,
    db: DbSession,
    #_user=Depends(require_permission("hce:alertas:read")),
):
    try:
        return await alerta_service.get_alertas_paciente(db, id_paciente)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )


@router.post(
    "/pacientes/{id_paciente}/alertas",
    response_model=AlertaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una alerta clínica",
    description="Crea una nueva consideración/alerta de seguridad para el paciente.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
    },
)
async def crear_alerta(
    id_paciente: int,
    body: AlertaCreate,
    db: DbSession,
    #_user=Depends(require_permission("hce:alertas:write")),
):
    try:
        alerta = await alerta_service.crear_alerta(db, id_paciente, body)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
    return AlertaSchema.model_validate(alerta)


@router.patch(
    "/pacientes/{id_paciente}/alertas/{id_alerta}",
    response_model=AlertaSchema,
    summary="Resolver una alerta clínica",
    description="Cambia el estado de la alerta a Resuelta y registra la resolución.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def resolver_alerta(
    id_paciente: int,
    id_alerta: int,
    body: AlertaUpdate,
    db: DbSession,
    #_user=Depends(require_permission("hce:alertas:write")),
):
    alerta = await alerta_service.resolver_alerta(db, id_paciente, id_alerta, body)
    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Alerta no encontrada para este paciente."},
        )
    return AlertaSchema.model_validate(alerta)

'''
@router.delete(
    "/pacientes/{id_paciente}/alertas/{id_alerta}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una alerta clínica",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def eliminar_alerta(
    id_paciente: int,
    id_alerta: int,
    db: DbSession,
    #_user=Depends(require_permission("hce:alertas:write")),
):
    eliminada = await alerta_service.eliminar_alerta(db, id_paciente, id_alerta)
    if not eliminada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Alerta no encontrada para este paciente."},
        )
'''
