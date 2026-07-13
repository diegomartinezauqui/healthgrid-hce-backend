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
    id_episodio: Optional[int] = None,
):
    recetas = await receta_service.get_recetas(
        db, estado=estado, id_paciente=id_paciente, desde_fecha=desde_fecha, id_episodio=id_episodio
    )

    # Optimización N+1: Cargar alertas de todos los pacientes únicos en una sola query
    from app.repositories.alerta_repository import alerta_repo
    ids_pacientes = list({r.id_paciente for r in recetas})
    alertas_list = await alerta_repo.get_activas_by_pacientes(db, ids_pacientes)
    
    # Agrupar por id_paciente para acceso O(1)
    alertas_por_paciente = {}
    for a in alertas_list:
        alertas_por_paciente.setdefault(a.id_paciente, []).append(a)

    data = []
    for receta in recetas:
        alertas = alertas_por_paciente.get(receta.id_paciente, [])
        data.append(
            RecetaMedicaDetallada(
                id_receta=receta.id_receta,
                id_paciente=receta.id_paciente,
                id_evolucion=receta.id_evolucion,
                estado=receta.estado,
                fecha_creacion=receta.fecha_creacion,
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
        fecha_creacion=receta.fecha_creacion,
        items=receta.items,
        alertas_clinicas=[
            AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
            for a in alertas
        ],
    )


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
async def registrar_receta(
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
            fecha_creacion=receta.fecha_creacion,
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


@router.patch(
    "/recetas/{id_receta}/dispensar",
    response_model=RecetaMedicaDetallada,
    summary="Marcar receta como dispensada",
    description=(
        "Permite al Módulo 3 (Farmacia) cambiar el estado de una receta a 'Dispensada'."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def dispensar_receta(
    id_receta: int,
    db: DbSession,
    _user=Depends(require_permission("hce:recetas:write")),
):
    try:
        receta = await receta_service.dispensar_receta(db, id_receta)
        if not receta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NOT_FOUND", "message": "La receta no existe o no fue encontrada."},
            )

        alertas = await receta_service.get_alertas_farmacologicas_paciente(
            db, receta.id_paciente
        )

        return RecetaMedicaDetallada(
            id_receta=receta.id_receta,
            id_paciente=receta.id_paciente,
            id_evolucion=receta.id_evolucion,
            estado=receta.estado,
            fecha_creacion=receta.fecha_creacion,
            items=receta.items,
            alertas_clinicas=[
                AlertaSmartPayload(tipo=a.tipo, severidad=a.severidad, descripcion=a.descripcion)
                for a in alertas
            ],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "UNPROCESSABLE_ENTITY", "message": str(e)},
        )


@router.get(
    "/medicamentos",
    summary="Consultar listado de medicamentos disponibles (Vademecum Mock)",
    description="Retorna una lista estática de medicamentos comunes para autocompletar en el frontend.",
)
async def listar_medicamentos(q: Optional[str] = None):
    meds = [
        {"id": 1, "nombre": "Ibuprofeno 600mg", "presentacion": "Comprimidos"},
        {"id": 2, "nombre": "Paracetamol 500mg", "presentacion": "Comprimidos"},
        {"id": 3, "nombre": "Amoxicilina 500mg", "presentacion": "Comprimidos"},
        {"id": 4, "nombre": "Clonazepam 2mg", "presentacion": "Comprimidos"},
        {"id": 5, "nombre": "Metformina 850mg", "presentacion": "Comprimidos"},
        {"id": 6, "nombre": "Losartán 50mg", "presentacion": "Comprimidos"},
        {"id": 7, "nombre": "Atorvastatina 20mg", "presentacion": "Comprimidos"},
        {"id": 8, "nombre": "Aspirina 100mg", "presentacion": "Comprimidos"},
        {"id": 9, "nombre": "Omeprazol 20mg", "presentacion": "Cápsulas"},
        {"id": 10, "nombre": "Enalapril 10mg", "presentacion": "Comprimidos"},
        {"id": 11, "nombre": "Sildenafil 50mg", "presentacion": "Comprimidos"},
        {"id": 12, "nombre": "Diclofenac 75mg", "presentacion": "Comprimidos"},
        {"id": 13, "nombre": "Loratadina 10mg", "presentacion": "Comprimidos"},
        {"id": 14, "nombre": "Levotiroxina 100mcg", "presentacion": "Comprimidos"},
        {"id": 15, "nombre": "Salbutamol Aerosol", "presentacion": "Inhalador"},
    ]
    if q:
        q_lower = q.lower()
        return [m for m in meds if q_lower in m["nombre"].lower()]
    return meds


