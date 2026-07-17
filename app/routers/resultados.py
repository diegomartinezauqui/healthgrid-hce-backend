"""
Endpoint de resultados de estudios — Integración M4/M5 → HCE.
M4/M5 envían resultados para vincularlos a la Historia Clínica.
"""

from fastapi import APIRouter, Depends, status, Request

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.resultado import (
    ResultadoCreatedResponse,
    ResultadoEstudioRequest,
    ResultadoLaboratorioWebhook,
)
from app.services import resultado_service
from app.integrations import m5_client

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


@router.get(
    "/resultados/imagenes/{report_id}/detalle",
    summary="Consultar detalle de un reporte específico en M5",
    description="Actúa como proxy hacia M5 para obtener el detalle de un informe clínico mediante su UUID.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_detalle_reporte_m5(
    report_id: str,
    request: Request,
    _user=Depends(require_permission("hce:resultados:read")),
):
    token = request.headers.get("Authorization")
    try:
        return await m5_client.obtener_reporte(report_id, token)
    except m5_client.M5IntegrationError as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": "M5_ERROR", "message": exc.message},
        )
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        )


@router.get(
    "/resultados/imagenes/{report_id}/imagenes",
    summary="Consultar imágenes de un reporte específico en M5",
    description="Actúa como proxy hacia M5 para obtener el listado de archivos/imágenes médicas asociadas a un informe clínico.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_imagenes_reporte_m5(
    report_id: str,
    request: Request,
    _user=Depends(require_permission("hce:resultados:read")),
):
    token = request.headers.get("Authorization")
    try:
        return await m5_client.obtener_imagenes(report_id, token)
    except m5_client.M5IntegrationError as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": "M5_ERROR", "message": exc.message},
        )
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        )

