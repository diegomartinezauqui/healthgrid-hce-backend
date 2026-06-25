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
    OrdenCreate,
    OrdenCreatedResponse,
    OrdenListResponse,
    OrdenMedicaCompleta,
    OrdenLaboratorioCreate,
    OrdenImagenCreate,
)
from common.enums.enums_orden import TipoEstudio
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
                id_episodio=orden.id_episodio,
                id_evolucion=orden.id_evolucion,
                fecha_creacion=orden.fecha_creacion,
                id_medico_solicitante=orden.id_medico_solicitante,
                subtipo=orden.subtipo,
                estudio_ids=orden.estudio_ids,
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
        id_episodio=orden.id_episodio,
        id_evolucion=orden.id_evolucion,
        fecha_creacion=orden.fecha_creacion,
        id_medico_solicitante=orden.id_medico_solicitante,
        subtipo=orden.subtipo,
        estudio_ids=orden.estudio_ids,
        alertas_clinicas=[
            AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
            for a in alertas
        ],
    )


@router.post(
    "/pacientes/{id_paciente}/ordenes",
    deprecated=True,
    response_model=OrdenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden médica de estudio",
    description=(
        "El médico genera una orden de estudio (Laboratorio, Imágenes o Anatomía Patológica) "
        "para un paciente dentro de un episodio activo. "
        "Al crearse, HCE publica automáticamente el evento Kafka "
        "`clinica.estudios.orden_creada` para que M4 (Laboratorio) y M5 (Imágenes) lo procesen. "
        "Permission claim requerido: `hce:ordenes:write`."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
        403: {"model": ErrorResponse, "description": "Sin permiso requerido."},
        422: {"model": ErrorResponse, "description": "Datos inválidos."},
    },
)
async def crear_orden(
    id_paciente: int,
    body: OrdenCreate,
    db: DbSession,
    _user=Depends(require_permission("hce:ordenes:write")),
):
    try:
        orden = await orden_service.crear_orden(
            db,
            id_paciente=id_paciente,
            tipo_estudio=body.tipo_estudio,
            descripcion_pedido=body.descripcion_pedido,
            prioridad=body.prioridad,
            id_episodio=body.id_episodio,
            id_evolucion=body.id_evolucion,
            id_medico_solicitante=_user.sub if hasattr(_user, "sub") else getattr(_user, "get", lambda k: None)("sub"),
        )
        return OrdenCreatedResponse(
            status="success",
            message="Orden creada y evento Kafka publicado.",
            id_orden=orden.id_orden,
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )


@router.post(
    "/pacientes/{id_paciente}/ordenes/laboratorio",
    response_model=OrdenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden médica de laboratorio (M4)",
    description=(
        "Crea una orden de laboratorio vinculando una lista de IDs de estudios del catálogo de M4. "
        "Notifica de forma asíncrona a M4 mediante HTTP y publica el evento en Kafka."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
        403: {"model": ErrorResponse, "description": "Sin permiso requerido."},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
        422: {"model": ErrorResponse, "description": "Datos inválidos."},
    },
)
async def crear_orden_laboratorio(
    id_paciente: int,
    body: OrdenLaboratorioCreate,
    db: DbSession,
    _user=Depends(require_permission("hce:ordenes:write")),
):
    try:
        orden = await orden_service.crear_orden(
            db,
            id_paciente=id_paciente,
            tipo_estudio=TipoEstudio.LABORATORIO,
            descripcion_pedido=body.descripcion_pedido,
            prioridad=body.prioridad,
            id_episodio=body.id_episodio,
            id_evolucion=body.id_evolucion,
            id_medico_solicitante=_user.sub if hasattr(_user, "sub") else getattr(_user, "get", lambda k: None)("sub"),
            estudio_ids=body.estudio_ids,
        )
        return OrdenCreatedResponse(
            status="success",
            message="Orden de laboratorio creada y notificada a M4.",
            id_orden=orden.id_orden,
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )


@router.post(
    "/pacientes/{id_paciente}/ordenes/imagenes",
    response_model=OrdenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden médica de imágenes diagnósticas (M5)",
    description=(
        "Crea una orden de diagnóstico por imágenes especificando la modalidad (subtipo). "
        "Notifica de forma asíncrona a M5 mediante HTTP y publica el evento en Kafka."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Token JWT ausente, inválido o expirado."},
        403: {"model": ErrorResponse, "description": "Sin permiso requerido."},
        404: {"model": ErrorResponse, "description": "Paciente no encontrado."},
        422: {"model": ErrorResponse, "description": "Datos inválidos."},
    },
)
async def crear_orden_imagenes(
    id_paciente: int,
    body: OrdenImagenCreate,
    db: DbSession,
    _user=Depends(require_permission("hce:ordenes:write")),
):
    try:
        orden = await orden_service.crear_orden(
            db,
            id_paciente=id_paciente,
            tipo_estudio=TipoEstudio.IMAGEN,
            descripcion_pedido=body.descripcion_pedido,
            prioridad=body.prioridad,
            id_episodio=body.id_episodio,
            id_evolucion=body.id_evolucion,
            id_medico_solicitante=_user.sub if hasattr(_user, "sub") else getattr(_user, "get", lambda k: None)("sub"),
            subtipo=body.subtipo,
        )
        return OrdenCreatedResponse(
            status="success",
            message="Orden de imágenes creada y notificada a M5.",
            id_orden=orden.id_orden,
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )
