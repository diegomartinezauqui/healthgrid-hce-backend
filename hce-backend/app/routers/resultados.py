"""
Endpoint de resultados de estudios — Integración M4/M5 → HCE.
M4/M5 envían resultados para vincularlos a la Historia Clínica.
"""

from fastapi import APIRouter, Depends, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.resultado import (
    ResultadoCreatedResponse,
    ResultadoEstudioRequest,
    ResultadoLaboratorioWebhook,
)
from app.services import resultado_service

router = APIRouter()


@router.post(
    "/resultados",
    response_model=ResultadoCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar resultado de estudio",
    description=(
        "Endpoint utilizado por M5 (Imágenes) u otros para registrar "
        "los resultados de un estudio médico finalizado en la HCE."
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


@router.post(
    "/resultados/laboratorio",
    deprecated=True,
    response_model=ResultadoCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Webhook para registrar resultados del Módulo 4 (Laboratorio)",
    description=(
        "Endpoint expuesto para que el Core envíe los eventos de tipo "
        "laboratorio.resultado_listo tras la suscripción."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse, "description": "Datos inválidos."},
    },
)
async def registrar_resultado_laboratorio(
    body: ResultadoLaboratorioWebhook,
    db: DbSession,
    _user=Depends(require_permission("hce:resultados:write")),
):
    await resultado_service.registrar_resultado_laboratorio(db, body)
    return ResultadoCreatedResponse(
        status="success",
        message="Resultado de laboratorio vinculado correctamente a la Historia Clínica.",
    )
