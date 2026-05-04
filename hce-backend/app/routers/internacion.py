"""
Endpoint de internación — Integración M6 (Camas) → HCE.
M6 notifica el ingreso físico de un paciente a una cama.
"""

from fastapi import APIRouter, Depends, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.internacion import IngresoInternacionRequest, IngresoInternacionResponse
from app.services import internacion_service

router = APIRouter()


@router.post(
    "/internacion/ingreso",
    response_model=IngresoInternacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Notificar ingreso de paciente (M6 → HCE)",
    description=(
        "Endpoint utilizado por el Módulo 6 para notificar a la HCE que un "
        "paciente fue ingresado físicamente a una cama. Esto dispara la "
        "creación del Episodio de Internación en la Historia Clínica."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse, "description": "Datos de ingreso inválidos."},
    },
)
async def notificar_ingreso(
    body: IngresoInternacionRequest,
    db: DbSession,
    _user=Depends(require_permission("hce:internacion:write")),
):
    result = await internacion_service.registrar_ingreso(db, body)
    return IngresoInternacionResponse(
        status="success",
        mensaje="Episodio creado y cama asignada correctamente.",
        data=result,
    )
