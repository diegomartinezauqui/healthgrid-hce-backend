"""
Integración con M10 (Core) — Notificación de cambios de permisos.
HCE llama a Core cuando detecta un cambio que impacta permisos.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.config import settings
from app.schemas.common import ErrorResponse
from app.schemas.kafka_events import PermissionChangeNotification, PermissionChangeResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/hce/notify-permission-change",
    response_model=PermissionChangeResponse,
    summary="Notificar a Core un cambio de permisos originado en HCE",
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def notify_permission_change(
    body: PermissionChangeNotification,
    _user=Depends(require_permission("hce:write")),
):
    """Proxy que reenvía la notificación al Módulo 10 (Core)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.CORE_BASE_URL}/hce/notify-permission-change",
                json=body.model_dump(mode="json"),
                timeout=10.0,
            )
            response.raise_for_status()
            return PermissionChangeResponse(acknowledged=True)
    except httpx.HTTPError as e:
        logger.error("Error notificando a Core: %s", e)
        return PermissionChangeResponse(acknowledged=True)
