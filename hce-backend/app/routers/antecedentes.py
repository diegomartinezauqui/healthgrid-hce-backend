"""
Endpoints de antecedentes clínicos del paciente.
CRUD completo para registro de historial clínico (quirúrgicos, familiares, patológicos, hábitos).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.antecedente import AntecedenteCreate, AntecedenteSchema, AntecedenteUpdate
from app.schemas.common import ErrorResponse
from app.services import antecedente_service

router = APIRouter()


@router.get(
    "/pacientes/{id_paciente}/antecedentes",
    response_model=list[AntecedenteSchema],
    summary="Listar antecedentes clínicos de un paciente",
    description="Retorna todos los antecedentes registrados del paciente.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
    },
)
async def listar_antecedentes(
    id_paciente: int,
    db: DbSession,
    #_user=Depends(require_permission("hce:antecedentes:read")),
):
    try:
        return await antecedente_service.get_antecedentes_paciente(db, id_paciente)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )


@router.post(
    "/pacientes/{id_paciente}/antecedentes",
    response_model=AntecedenteSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un antecedente clínico",
    description="Agrega un nuevo antecedente al historial clínico del paciente.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
    },
)
async def crear_antecedente(
    id_paciente: int,
    body: AntecedenteCreate,
    db: DbSession,
    #_user=Depends(require_permission("hce:antecedentes:write")),
):
    try:
        antecedente = await antecedente_service.crear_antecedente(db, id_paciente, body)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
    return AntecedenteSchema.model_validate(antecedente)


@router.patch(
    "/pacientes/{id_paciente}/antecedentes/{id_antecedente}",
    response_model=AntecedenteSchema,
    summary="Actualizar un antecedente clínico",
    description="Actualización parcial de un antecedente. Solo se pisan los campos enviados.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def actualizar_antecedente(
    id_paciente: int,
    id_antecedente: int,
    body: AntecedenteUpdate,
    db: DbSession,
    #_user=Depends(require_permission("hce:antecedentes:write")),
):
    antecedente = await antecedente_service.actualizar_antecedente(
        db, id_paciente, id_antecedente, body
    )
    if not antecedente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Antecedente no encontrado para este paciente."},
        )
    return AntecedenteSchema.model_validate(antecedente)

'''
@router.delete(
    "/pacientes/{id_paciente}/antecedentes/{id_antecedente}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un antecedente clínico",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def eliminar_antecedente(
    id_paciente: int,
    id_antecedente: int,
    db: DbSession,
    #_user=Depends(require_permission("hce:antecedentes:write")),
):
    eliminado = await antecedente_service.eliminar_antecedente(
        db, id_paciente, id_antecedente
    )
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Antecedente no encontrado para este paciente."},
        )
'''
