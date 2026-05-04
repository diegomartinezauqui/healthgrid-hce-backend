"""
Endpoints de historial del paciente — Integración M8 (Portal del Paciente).
HCE expone → Portal consume para sección "Mi Salud".
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.receta import AlertaFarmacologicaSchema, RecetaMedicaDetallada
from app.schemas.resultado import ResultadoEstudioResumen
from app.services import receta_service, resultado_service

router = APIRouter()


@router.get(
    "/pacientes/{id_paciente}/historial/recetas",
    response_model=List[RecetaMedicaDetallada],
    summary="Consultar historial de recetas del paciente (Para M8)",
    description=(
        "Endpoint sincrónico consumido por el Portal del Paciente (M8) "
        "para renderizar la sección 'Mi Salud', listando todas las recetas."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def historial_recetas(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:recetas:read")),
):
    recetas = await receta_service.get_recetas(db, id_paciente=id_paciente)
    alertas = await receta_service.get_alertas_farmacologicas_paciente(db, id_paciente)
    alertas_schema = [
        AlertaFarmacologicaSchema(tipo=a.tipo, descripcion=a.descripcion)
        for a in alertas
    ]

    return [
        RecetaMedicaDetallada(
            id_receta=r.id_receta,
            id_paciente=r.id_paciente,
            id_evolucion=r.id_evolucion,
            medicamento=r.medicamento,
            indicaciones=r.indicaciones,
            estado=r.estado,
            alertas_farmacologicas=alertas_schema,
        )
        for r in recetas
    ]


@router.get(
    "/pacientes/{id_paciente}/historial/resultados",
    response_model=List[ResultadoEstudioResumen],
    summary="Consultar resultados de estudios del paciente (Para M8)",
    description=(
        "Endpoint sincrónico consumido por el Portal del Paciente (M8) "
        "para mostrar los resultados de estudios médicos finalizados."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def historial_resultados(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:resultados:read")),
):
    resultados = await resultado_service.get_resultados_paciente(db, id_paciente)

    return [
        ResultadoEstudioResumen(
            id_resultado=r.id_resultado,
            tipo_estudio=r.tipo_estudio,
            fecha_resultado=r.fecha_resultado,
            titulo=r.titulo,
            resumen=r.resumen,
            profesional_firmante=r.id_profesional_firmante,
        )
        for r in resultados
    ]
