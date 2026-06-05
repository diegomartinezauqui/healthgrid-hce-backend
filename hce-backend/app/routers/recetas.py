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


# ═══════════════════════════════════════════════════════════════════
# RECETAS DE LA EVOLUCIÓN (HCE)
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/patients/{id_paciente}/episodes/{id_episodio}/evoluciones/{id_evolucion}/recetas",
    response_model=RecetaMedicaDetallada,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una receta médica",
    description=(
        "Permite al médico registrar una receta electrónica asociada a la nota de evolución. "
        "Admite múltiples medicamentos. Al guardarse, se notifica automáticamente a Farmacia."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def crear_receta(
    id_paciente: int,
    id_episodio: int,
    id_evolucion: int,
    body: RecetaCreate,
    db: DbSession,
    user=Depends(require_permission("hce:recetas:write")),
):
    try:
        # Validamos que la evolución exista y pertenezca al episodio/paciente
        evolucion = await evolucion_service.get_evolucion_detalle(
            db, id_paciente, id_episodio, id_evolucion
        )
        if not evolucion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NOT_FOUND", "message": "La evolución solicitada no fue encontrada."},
            )
            
        receta = await receta_service.registrar_receta(
            db, id_paciente, id_episodio, id_evolucion, body
        )
        
        alertas = await receta_service.get_alertas_farmacologicas_paciente(
            db, id_paciente
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
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "UNPROCESSABLE_ENTITY", "message": str(e)},
        )
