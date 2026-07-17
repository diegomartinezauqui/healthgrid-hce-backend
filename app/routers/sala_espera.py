"""
Endpoints de Sala de Espera — Gestión de pacientes en espera, llamados y atención.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.permissions import require_permission
from app.auth.jwt_handler import security, HTTPAuthorizationCredentials
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.sala_espera import (
    SalaEsperaCreate,
    SalaEsperaLlamar,
    SalaEsperaSchema,
    SalaEsperaAtender,
    SalaEsperaPrioridad,
)
from app.services import sala_espera_service

router = APIRouter()


@router.get(
    "/sala-espera",
    response_model=List[SalaEsperaSchema],
    summary="Listar pacientes en la sala de espera",
    description=(
        "Obtiene los registros de la sala de espera aplicando filtros por médico, sede y estado. "
        "Permite ordenar de forma flexible por llegada (orden de llegada), turno o prioridad."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def listar_sala_espera(
    db: DbSession,
    id_medico: Optional[int] = Query(None, description="Filtrar por médico asignado"),
    id_sede: Optional[int] = Query(None, description="Filtrar por sede física"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (Esperando, Llamado, Atendido, Ausente)"),
    ordenar_por: Optional[str] = Query(
        None, description="Criterio de ordenamiento: 'llegada' (por defecto), 'turno', 'prioridad'"
    ),
    _user=Depends(require_permission("hce:episodes:read")),
):
    registros = await sala_espera_service.get_sala_espera(
        db, id_medico=id_medico, id_sede=id_sede, estado=estado, ordenar_por=ordenar_por
    )
    return registros


@router.post(
    "/sala-espera/ingreso",
    response_model=SalaEsperaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ingreso manual a la sala de espera",
    description=(
        "Registra de forma manual la llegada de un paciente. "
        "Si no existe un episodio consulta-externa abierto para el médico y sede, lo crea automáticamente."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
    },
)
async def ingresar_paciente_manual(
    body: SalaEsperaCreate,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:write")),
):
    try:
        registro = await sala_espera_service.ingresar_paciente(db, body.id_paciente, body)
        return registro
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )


@router.patch(
    "/sala-espera/{id_espera}/llamar",
    response_model=SalaEsperaSchema,
    summary="Llamar a un paciente asignando consultorio",
    description="Cambia el estado del paciente a 'Llamado' y le asigna un número de consultorio.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Registro no encontrado."},
    },
)
async def llamar_paciente(
    id_espera: int,
    body: SalaEsperaLlamar,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:write")),
):
    registro = await sala_espera_service.llamar_paciente(db, id_espera, body.consultorio)
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "No se encontró el registro de sala de espera solicitado."},
        )
    return registro


@router.patch(
    "/sala-espera/{id_espera}/atender",
    response_model=SalaEsperaSchema,
    summary="Marcar paciente como siendo atendido",
    description="Cambia el estado del paciente a 'Atendido' y opcionalmente asocia un episodio médico existente o crea uno nuevo.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Registro no encontrado."},
        400: {"model": ErrorResponse, "description": "Episodio médico inválido para este paciente."},
    },
)
async def atender_paciente(
    id_espera: int,
    db: DbSession,
    body: Optional[SalaEsperaAtender] = None,
    _user=Depends(require_permission("hce:episodes:write")),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        id_episodio = body.id_episodio if body else None
        token_auth = f"Bearer {credentials.credentials}" if credentials else None
        registro = await sala_espera_service.atender_paciente(db, id_espera, id_episodio=id_episodio, token_auth=token_auth)
        if not registro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NOT_FOUND", "message": "No se encontró el registro de sala de espera solicitado."},
            )
        return registro
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BAD_REQUEST", "message": str(e)},
        )


@router.patch(
    "/sala-espera/{id_espera}/ausente",
    response_model=SalaEsperaSchema,
    summary="Marcar paciente como ausente",
    description="Cambia el estado del paciente a 'Ausente'.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Registro no encontrado."},
    },
)
async def marcar_ausente(
    id_espera: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:write")),
):
    registro = await sala_espera_service.marcar_ausente(db, id_espera)
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "No se encontró el registro de sala de espera solicitado."},
        )
    return registro


@router.patch(
    "/sala-espera/{id_espera}/prioridad",
    response_model=SalaEsperaSchema,
    summary="Actualizar prioridad del paciente (Triage)",
    description="Permite a los módulos de Triage/M9 o enfermería reclasificar la prioridad del paciente en la sala de espera.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Registro no encontrado."},
    },
)
async def actualizar_prioridad(
    id_espera: int,
    body: SalaEsperaPrioridad,
    db: DbSession,
    user=Depends(require_permission("hce:episodes:write")),
):
    registro = await sala_espera_service.actualizar_prioridad(db, id_espera, body.prioridad, body.motivo, body.id_medico_triage or user.sub)
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "No se encontró el registro de sala de espera solicitado."},
        )
    return registro


@router.patch(
    "/sala-espera/{id_espera}/finalizar",
    response_model=SalaEsperaSchema,
    summary="Marcar turno como finalizado",
    description="Cambia el estado del paciente a 'Finalizado' al concluir la atención médica.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Registro no encontrado."},
    },
)
async def finalizar_paciente(
    id_espera: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:write")),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    token_auth = f"Bearer {credentials.credentials}" if credentials else None
    registro = await sala_espera_service.finalizar_paciente(db, id_espera, token_auth=token_auth)
    if not registro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "No se encontró el registro de sala de espera solicitado."},
        )
    return registro

