"""
Endpoints proxy para el Nomenclador Médico, Obras Sociales y Planes (Integración M7 Facturación).
Evita problemas de CORS en el frontend canalizando las llamadas de forma segura.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.permissions import require_permission
from app.schemas.common import ErrorResponse
from app.services import m7_client

router = APIRouter(prefix="/nomenclador", tags=["Integración M7 (Facturación)"])


@router.get(
    "/prestaciones",
    summary="Consultar nomenclador médico de M7",
    description=(
        "Obtiene el catálogo de prestaciones facturables administrado por el Módulo 7. "
        "Permite buscar por código, descripción o tipo de prestación. Reenvía el token JWT."
    ),
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def consultar_nomenclador(
    request: Request,
    codigo: Optional[str] = Query(None, description="Filtro por código del nomenclador"),
    descripcion: Optional[str] = Query(None, description="Filtro por nombre/descripción de la prestación"),
    tipo: Optional[str] = Query(None, description="Filtro por tipo. Valores: CONSULTA, PRACTICA, LABORATORIO, INSUMO"),
    _user=Depends(require_permission("hce:episodes:read")),
):
    auth_header = request.headers.get("Authorization")
    token = auth_header.replace("Bearer ", "") if auth_header else None

    try:
        return await m7_client.buscar_prestaciones_nomenclador(
            codigo=codigo,
            descripcion=descripcion,
            tipo_prestacion=tipo,
            token=token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        )


@router.get(
    "/obras-sociales",
    summary="Consultar entidades financiadoras de M7",
    description="Retorna el catálogo de obras sociales y prepagas activas registradas en Facturación (M7).",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def consultar_obras_sociales(
    request: Request,
    _user=Depends(require_permission("hce:episodes:read")),
):
    auth_header = request.headers.get("Authorization")
    token = auth_header.replace("Bearer ", "") if auth_header else None

    try:
        return await m7_client.buscar_entidades_financiadoras(token=token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        )


@router.get(
    "/planes",
    summary="Consultar planes de obras sociales de M7",
    description="Retorna el catálogo de planes de prepagas u obras sociales. Permite filtrar por obra social.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def consultar_planes(
    request: Request,
    entidad_financiadora_id: Optional[int] = Query(None, description="Filtrar planes de una obra social específica"),
    _user=Depends(require_permission("hce:episodes:read")),
):
    auth_header = request.headers.get("Authorization")
    token = auth_header.replace("Bearer ", "") if auth_header else None

    try:
        return await m7_client.buscar_planes(
            entidad_financiadora_id=entidad_financiadora_id,
            token=token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(exc)},
        )
