"""
Endpoints de ficha médica — Gestión interna del módulo HCE.
Permite crear y consultar la ficha clínica permanente de un paciente.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.ficha_medica import (
    FichaMedicaCreate,
    FichaMedicaSchema,
    FichaMedicaUpdate,
    FichaMedicaCompletaCreate,
    FichaMedicaCompletaResponse,
)
from app.services import ficha_medica_service

router = APIRouter()


@router.post(
    "/pacientes/{id_paciente}/ficha-medica",
    response_model=FichaMedicaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear ficha médica de un paciente",
    description=(
        "Crea la ficha médica permanente de un paciente en la Historia Clínica. "
        "Contiene datos clínicos estáticos como grupo sanguíneo, peso, altura y "
        "observaciones generales. Solo puede existir una ficha por paciente."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Ya existe una ficha médica para este paciente."},
    },
)
async def crear_ficha_medica(
    id_paciente: int,
    body: FichaMedicaCreate,
    db: DbSession,
    _user=Depends(require_permission("hce:ficha-medica:write")),
):
    try:
        ficha = await ficha_medica_service.crear_ficha_medica(db, id_paciente, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": str(e)},
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
    return FichaMedicaSchema.model_validate(ficha)


@router.get(
    "/pacientes/{id_paciente}/ficha-medica",
    response_model=FichaMedicaSchema,
    summary="Obtener ficha médica de un paciente",
    description="Retorna los datos clínicos permanentes del paciente registrados en su ficha médica.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_ficha_medica(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:ficha-medica:read")),
):
    ficha = await ficha_medica_service.get_ficha_medica(db, id_paciente)
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "No se encontró la ficha médica para este paciente."},
        )
    return FichaMedicaSchema.model_validate(ficha)


@router.patch(
    "/pacientes/{id_paciente}/ficha-medica",
    response_model=FichaMedicaSchema,
    summary="Actualizar ficha médica de un paciente",
    description=(
        "Actualiza parcialmente la ficha médica del paciente. "
        "Solo se modifican los campos enviados en el body."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def actualizar_ficha_medica(
    id_paciente: int,
    body: FichaMedicaUpdate,
    db: DbSession,
    _user=Depends(require_permission("hce:ficha-medica:write")),
):
    ficha = await ficha_medica_service.actualizar_ficha_medica(db, id_paciente, body)
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "No se encontró la ficha médica para este paciente."},
        )
    return FichaMedicaSchema.model_validate(ficha)


@router.post(
    "/pacientes/{id_paciente}/ficha-completa",
    response_model=FichaMedicaCompletaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ficha médica completa (con antecedentes y alertas)",
    description=(
        "Crea de forma atómica la ficha médica del paciente junto con "
        "sus antecedentes y alertas clínicas en una sola transacción."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
        409: {"model": ErrorResponse, "description": "Ya existe una ficha médica para este paciente."},
    },
)
async def crear_ficha_medica_completa(
    id_paciente: int,
    body: FichaMedicaCompletaCreate,
    db: DbSession,
    user=Depends(require_permission("hce:ficha-medica:write")),
):
    try:
        return await ficha_medica_service.crear_ficha_medica_completa(
            db, id_paciente, body, user.sub
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": str(e)},
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )

