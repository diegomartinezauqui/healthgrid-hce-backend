"""
Servicio de suscripción de eventos ante el Core.
HCE se registra automáticamente al iniciar la aplicación para recibir
notificaciones de resultados del Módulo 4 (Laboratorio) y Módulo 5 (Imágenes).
"""

import asyncio
import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def _get_auth_headers(client: httpx.AsyncClient) -> dict:
    if not settings.CORE_SERVICE_EMAIL or not settings.CORE_SERVICE_PASSWORD:
        logger.warning("⚠️ Faltan credenciales del Core para autenticación en suscripciones.")
        return {}
    try:
        resp = await client.post(
            f"{settings.CORE_API_URL}/auth/login",
            json={"email": settings.CORE_SERVICE_EMAIL, "password": settings.CORE_SERVICE_PASSWORD},
            timeout=4.0
        )
        if resp.status_code == 200:
            token = resp.json().get("token") or resp.json().get("access_token")
            if token:
                return {"Authorization": f"Bearer {token}"}
        logger.warning("⚠️ Error al obtener token de suscripción. Status %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.warning("⚠️ Error de conexión para obtener token de suscripción: %s", e)
    return {}


async def registrar_suscripciones_core():
    """
    (Deshabilitado - Las suscripciones HTTP ya no se usan en el Core, se utiliza RabbitMQ).
    """
    pass
