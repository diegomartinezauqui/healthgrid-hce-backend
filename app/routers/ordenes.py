"""
Endpoints de órdenes médicas — Integración M4/M5 (Estudios).
HCE expone → Laboratorio e Imágenes consumen.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.permissions import require_permission
from app.auth.jwt_handler import security, HTTPAuthorizationCredentials
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
from common.enums.enums_orden import TipoEstudio, OrigenOrden
from app.services import orden_service, resultado_service
from app.schemas.resultado import ResultadoEstudioResumen

router = APIRouter()


@router.get(
    "/analitos/laboratorio",
    summary="Listar analitos disponibles en M4 (catálogo de laboratorio)",
    description=(
        "Consulta el catálogo de analitos del Módulo 4 (Laboratorio). "
        "El médico selecciona los analitos deseados de esta lista para luego crear la orden. "
        "Filtro opcional por categoría: `Hematologia`, `Bioquimica`, `Orina`."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        502: {"model": ErrorResponse, "description": "M4 no disponible."},
    },
)
async def listar_analitos(
    _user=Depends(require_permission("hce:ordenes:read")),
    categoria: Optional[str] = Query(
        None,
        description="Categoría para filtrar analitos (ej: Hematologia, Bioquimica, Orina).",
        examples=["Hematologia"],
    ),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    from app.integrations import m4_client
    token_auth = f"Bearer {credentials.credentials}" if credentials else None
    try:
        analitos = await m4_client.obtener_analitos(categoria=categoria, token_auth=token_auth)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "M4_UNAVAILABLE", "message": f"No se pudo obtener el catálogo de M4: {exc}"},
        )
    return {"status": "success", "cantidad": len(analitos), "data": analitos}



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

    # Optimización N+1: Cargar alertas de todos los pacientes únicos en una sola query
    from app.repositories.alerta_repository import alerta_repo
    ids_pacientes = list({o.id_paciente for o in ordenes})
    alertas_list = await alerta_repo.get_activas_by_pacientes(db, ids_pacientes)
    
    # Agrupar por id_paciente para acceso O(1)
    alertas_por_paciente = {}
    for a in alertas_list:
        alertas_por_paciente.setdefault(a.id_paciente, []).append(a)

    data = []
    for orden in ordenes:
        alertas = alertas_por_paciente.get(orden.id_paciente, [])
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
                estado=orden.estado,
                origen=orden.origen,
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
    summary="Obtener detalles de una orden (Smart Payload con alertas clínicas)",
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
        estado=orden.estado,
        origen=orden.origen,
        alertas_clinicas=[
            AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
            for a in alertas
        ],
    )


@router.get(
    "/ordenes/{id_orden}/resultado",
    response_model=ResultadoEstudioResumen,
    summary="Obtener resultado de una orden por su ID y tipo",
    description=(
        "Permite recuperar el resultado clínico (analitos o informe PACS) "
        "asociado a una orden médica en base a su ID y el tipo de estudio."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def obtener_resultado_orden(
    id_orden: int,
    tipo_estudio: TipoEstudio,
    db: DbSession,
    _user=Depends(require_permission("hce:resultados:read")),
):
    resultado = await resultado_service.get_resultado_by_orden(
        db, id_orden=id_orden, tipo_estudio=tipo_estudio
    )
    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "El resultado para la orden especificada no fue encontrado."},
        )
    return resultado


@router.get(
    "/pacientes/{id_paciente}/ordenes",
    response_model=OrdenListResponse,
    summary="Listar órdenes de un paciente",
    description="Retorna todas las órdenes médicas (bioquímicas y de imágenes) de un paciente.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def listar_ordenes_paciente(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:ordenes:read")),
):
    ordenes = await orden_service.get_ordenes_paciente(db, id_paciente=id_paciente)

    # Optimización N+1: Consultar alertas una única vez
    alertas = await orden_service.get_alertas_clinicas_paciente(db, id_paciente)

    data = []
    for orden in ordenes:
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
                estado=orden.estado,
                origen=orden.origen,
                alertas_clinicas=[
                    AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
                    for a in alertas
                ],
            )
        )

    return OrdenListResponse(status="success", cantidad=len(data), data=data)


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
            origen=body.origen,
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
        "Crea una orden de laboratorio vinculando una lista de IDs de estudios del catálogo de M4."
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        token_auth = f"Bearer {credentials.credentials}" if credentials else None
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
            origen=body.origen,
            token_auth=token_auth,
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
        "Si se asocia a un eposiodo (id_episodio) o evolución (id_evolucion), se requiere que existan en el sistema."
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    try:
        token_auth = f"Bearer {credentials.credentials}" if credentials else None
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
            origen=body.origen,
            token_auth=token_auth,
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
