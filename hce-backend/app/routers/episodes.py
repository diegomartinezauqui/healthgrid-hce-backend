"""
Endpoints de episodios y actos médicos — Integración M7 (Facturación).
HCE expone → Facturación consume para liquidación.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.episodio import (
    ActoMedicoListResponse,
    ActoMedicoSchema,
    EpisodioDetalle,
    EpisodioListResponse,
    EpisodioResumen,
)
from app.services import episodio_service

router = APIRouter()


@router.get(
    "/patients/{id_paciente}/episodes",
    response_model=EpisodioListResponse,
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
    episodios = await episodio_service.get_episodios_paciente(
        db, id_paciente, estado=estado, desde_fecha=desde_fecha, hasta_fecha=hasta_fecha
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


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}",
    response_model=EpisodioDetalle,
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
    episodio = await episodio_service.get_episodio_detalle(db, id_paciente, id_episodio)
    if not episodio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El recurso solicitado no fue encontrado."},
        )

    return EpisodioDetalle(
        id_episodio=episodio.id_episodio,
        id_paciente=episodio.id_paciente,
        tipo=episodio.tipo,
        estado=episodio.estado,
        id_sede=episodio.id_sede,
        id_medico_responsable=episodio.id_medico_responsable,
        diagnostico_principal=episodio.diagnostico_principal,
        fecha_apertura=episodio.fecha_apertura,
        fecha_cierre=episodio.fecha_cierre,
        actos_medicos=[
            ActoMedicoSchema(
                id_acto_medico=am.id_acto_medico,
                id_episodio=am.id_episodio,
                codigo_nomenclador=am.codigo_nomenclador,
                descripcion=am.descripcion,
                tipo=am.tipo,
                id_profesional=am.id_profesional,
                fecha_realizacion=am.fecha_realizacion,
                cantidad=am.cantidad,
                observaciones=am.observaciones,
            )
            for am in episodio.actos_medicos
        ],
    )


@router.get(
    "/patients/{id_paciente}/episodes/{id_episodio}/medical-acts",
    response_model=ActoMedicoListResponse,
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
            ActoMedicoSchema(
                id_acto_medico=am.id_acto_medico,
                id_episodio=am.id_episodio,
                codigo_nomenclador=am.codigo_nomenclador,
                descripcion=am.descripcion,
                tipo=am.tipo,
                id_profesional=am.id_profesional,
                fecha_realizacion=am.fecha_realizacion,
                cantidad=am.cantidad,
                observaciones=am.observaciones,
            )
            for am in actos
        ],
    )
