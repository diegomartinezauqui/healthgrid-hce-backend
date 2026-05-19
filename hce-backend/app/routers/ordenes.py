"""
Endpoints de órdenes médicas — Integración M4/M5 (Estudios).
HCE expone → Laboratorio e Imágenes consumen.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.alerta import AlertaSmartPayload
from app.schemas.orden import (
    OrdenListResponse,
    OrdenMedicaCompleta,
)
from app.services import orden_service

router = APIRouter()


@router.get(
    "/ordenes",
    response_model=OrdenListResponse,
    summary="Consultar órdenes pendientes (sincronización masiva)",
    description=(
        "Endpoint utilizado por M4 y M5 como red de seguridad para consultar "
        "lotes completos de estudios pendientes."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def listar_ordenes(
    tipo_estudio: str,
    db: DbSession,
    _user=Depends(require_permission("hce:ordenes:read")),
    estado: Optional[str] = "Pendiente",
):
    ordenes = await orden_service.get_ordenes(db, tipo_estudio=tipo_estudio, estado=estado)

    data = []
    for orden in ordenes:
        alertas = await orden_service.get_alertas_clinicas_paciente(db, orden.id_paciente)
        data.append(
            OrdenMedicaCompleta(
                id_orden=orden.id_orden,
                id_paciente=orden.id_paciente,
                tipo_estudio=orden.tipo_estudio,
                descripcion_pedido=orden.descripcion_pedido,
                prioridad=orden.prioridad,
                alertas_clinicas=[
                    AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
                    for a in alertas
                ],
            )
        )

    return OrdenListResponse(status="success", cantidad=len(data), data=data)


@router.get(
    "/ordenes/{id_orden}",
    response_model=OrdenMedicaCompleta,
    summary="Obtener detalles de orden (Smart Payload con alertas clínicas)",
    description=(
        "Endpoint utilizado por M4 y M5 para descargar la información clínica "
        "de la orden y las alertas de seguridad."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_orden(
    id_orden: int,
    db: DbSession,
    _user=Depends(require_permission("hce:ordenes:read")),
):
    orden = await orden_service.get_orden_by_id(db, id_orden)
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El recurso solicitado no fue encontrado."},
        )

    alertas = await orden_service.get_alertas_clinicas_paciente(db, orden.id_paciente)

    return OrdenMedicaCompleta(
        id_orden=orden.id_orden,
        id_paciente=orden.id_paciente,
        tipo_estudio=orden.tipo_estudio,
        descripcion_pedido=orden.descripcion_pedido,
        prioridad=orden.prioridad,
        alertas_clinicas=[
            AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
            for a in alertas
        ],
    )
