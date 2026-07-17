"""
Endpoints de Pacientes — Consulta de datos demográficos cacheados localmente.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.paciente import PacienteSchema
from app.repositories.paciente_repository import paciente_repo

router = APIRouter()


@router.get(
    "/pacientes",
    response_model=List[PacienteSchema],
    summary="Listar pacientes cacheados",
    description="Retorna la lista de pacientes almacenados localmente en la caché de HCE.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def listar_pacientes(
    db: DbSession,
    email: Optional[str] = Query(None, description="Filtrar por email (sincroniza con el Core si no está en la caché)"),
    skip: int = Query(0, ge=0, description="Registros a omitir para paginación"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros a retornar"),
    _user=Depends(require_permission("hce:episodes:read")),
):
    if email:
        from app.services.core_patient_sync import get_or_create_patient_by_email
        paciente = await get_or_create_patient_by_email(db, email)
        return [paciente] if paciente else []

    pacientes = await paciente_repo.get_all(db, skip=skip, limit=limit)
    return pacientes


@router.get(
    "/pacientes/{id_paciente}",
    response_model=PacienteSchema,
    summary="Obtener un paciente por ID",
    description="Busca un paciente específico en la caché local de HCE por su ID.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
    },
)
async def obtener_paciente(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:read")),
):
    from app.services.core_patient_sync import get_or_create_patient_from_core
    paciente = await get_or_create_patient_from_core(db, id_paciente)
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": f"No se encontró el paciente con ID {id_paciente} en la caché ni en el Core."},
        )
    return paciente
