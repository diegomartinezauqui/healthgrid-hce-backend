"""
Endpoint de resultados de estudios — Integración M4/M5 → HCE.
M4/M5 envían resultados para vincularlos a la Historia Clínica.
"""

from fastapi import APIRouter, Depends, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.resultado import ResultadoCreatedResponse, ResultadoEstudioRequest
from app.services import resultado_service

router = APIRouter()


@router.post(
    "/resultados",
    response_model=ResultadoCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar resultado de estudio",
    description=(
        "Endpoint utilizado por M4 (Laboratorio) y M5 (Imágenes) para enviar "
        "los resultados de un estudio médico finalizado a la HCE."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse, "description": "Datos inválidos."},
    },
)
async def registrar_resultado(
    body: ResultadoEstudioRequest,
    db: DbSession,
    _user=Depends(require_permission("hce:resultados:write")),
):
    await resultado_service.registrar_resultado(db, body)
    return ResultadoCreatedResponse(
        status="success",
        message="Resultado vinculado correctamente a la Historia Clínica.",
    )
