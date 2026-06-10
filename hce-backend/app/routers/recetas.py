"""
Endpoints de recetas — Integración M3 (Farmacia).
HCE expone → Farmacia consume.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.dependencies import DbSession
from app.schemas.common import ErrorResponse
from app.schemas.receta import (
    RecetaCreate,
    RecetaCreatedResponse,
    RecetaListResponse,
    RecetaMedicaDetallada,
)
from app.schemas.alerta import AlertaSmartPayload
from app.services import evolucion_service, receta_service

router = APIRouter()


@router.get(
    "/recetas",
    response_model=RecetaListResponse,
    summary="Consultar listado de recetas (sincronización masiva)",
    description=(
        "Permite al Módulo 3 (Farmacia) obtener todas las recetas generadas. "
        "Útil para auditorías, cierres de lote o recuperación de datos tras caídas de Kafka."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
        403: {"model": ErrorResponse, "description": "Sin permiso requerido."},
    },
)
async def listar_recetas(
    db: DbSession,
    _user=Depends(require_permission("hce:recetas:read")),
    estado: Optional[str] = None,
    id_paciente: Optional[int] = None,
    desde_fecha: Optional[date] = None,
):
    recetas = await receta_service.get_recetas(
        db, estado=estado, id_paciente=id_paciente, desde_fecha=desde_fecha
    )

    data = []
    for receta in recetas:
        alertas = await receta_service.get_alertas_farmacologicas_paciente(
            db, receta.id_paciente
        )
        data.append(
            RecetaMedicaDetallada(
                id_receta=receta.id_receta,
                id_paciente=receta.id_paciente,
                id_evolucion=receta.id_evolucion,
                estado=receta.estado,
                items=receta.items,
                alertas_clinicas=[
                    AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
                    for a in alertas
                ],
            )
        )

    return RecetaListResponse(total=len(data), data=data)


@router.get(
    "/recetas/{id_receta}",
    response_model=RecetaMedicaDetallada,
    summary="Obtener detalles de receta (con alertas farmacológicas)",
    description=(
        "Endpoint al que Farmacia llama tras recibir el evento Kafka "
        "clinica.farmacia.receta_creada para obtener la medicación recetada "
        "y cruzarla con las alergias del paciente."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_receta(
    id_receta: int,
    db: DbSession,
    _user=Depends(require_permission("hce:recetas:read")),
):
    receta = await receta_service.get_receta_by_id(db, id_receta)
    if not receta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El recurso solicitado no fue encontrado."},
        )

    alertas = await receta_service.get_alertas_farmacologicas_paciente(
        db, receta.id_paciente
    )

    return RecetaMedicaDetallada(
        id_receta=receta.id_receta,
        id_paciente=receta.id_paciente,
        id_evolucion=receta.id_evolucion,
        estado=receta.estado,
        items=receta.items,
        alertas_clinicas=[
            AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
            for a in alertas
        ],
    )


@router.post(
    "/pacientes/{id_paciente}/recetas",
    response_model=RecetaCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear receta electrónica (prescripción médica)",
    description=(
        "El médico prescribe una receta electrónica para un paciente dentro de una evolución médica. "
        "Al crearse, HCE publica automáticamente el evento Kafka "
        "`clinica.farmacia.receta_creada` para que M3 (Farmacia) lo procese "
        "y disponga la medicación. "
        "Permission claim requerido: `hce:recetas:write`."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
        403: {"model": ErrorResponse, "description": "Sin permiso requerido."},
        422: {"model": ErrorResponse, "description": "Datos inválidos."},
    },
)
async def crear_receta(
    id_paciente: int,
    body: RecetaCreate,
    db: DbSession,
    _user=Depends(require_permission("hce:recetas:write")),
):
    receta = await receta_service.crear_receta(
        db,
        id_paciente=id_paciente,
        medicamento=body.medicamento,
        tipo_paciente=body.tipo_paciente,
        id_evolucion=body.id_evolucion,
        indicaciones=body.indicaciones,
    )
    return RecetaCreatedResponse(
        status="success",
        message="Receta creada y evento Kafka publicado.",
        id_receta=receta.id_receta,
    )
