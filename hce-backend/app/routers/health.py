"""
Health check del módulo HCE.
Endpoint sin autenticación usado por Core (M10) para monitorear disponibilidad.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get(
    "/hce/health",
    response_model=HealthResponse,
    summary="Health check del módulo HCE",
    description=(
        "Endpoint de estado que Core puede usar para monitorear "
        "la disponibilidad del módulo HCE. No requiere autenticación."
    ),
)
async def health_check():
    return HealthResponse(
        status="UP",
        module="hce",
        timestamp=datetime.now(timezone.utc),
    )
