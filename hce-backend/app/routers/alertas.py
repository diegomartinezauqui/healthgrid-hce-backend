"""
Endpoint de alertas clínicas — Integración M9 (Monitoreo).
"""

from typing import List

from fastapi import APIRouter, Depends

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.orden import AlertaClinicaSchema
from app.services import alerta_service

router = APIRouter()


@router.get(
    "/pacientes/{id_paciente}/alertas",
    response_model=List[AlertaClinicaSchema],
    summary="Consultar alertas clínicas del paciente (Para M9)",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def obtener_alertas(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:contraindications:read")),
):
    alertas = await alerta_service.get_alertas_paciente(db, id_paciente)
    return [
        AlertaClinicaSchema(tipo=a.tipo, descripcion=a.descripcion)
        for a in alertas
    ]
