"""
Client hacia el Módulo 2 (Gestión de Turnos y Agendas).

Contrato de comunicación:
  - PATCH /appointments/<id>/start -> Inicia el turno en M2 (estado checked_in -> in_progress)
  - PATCH /appointments/<id>/finish -> Finaliza el turno en M2 (estado in_progress -> completed)
"""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def iniciar_turno(id_turno_m2: int, token_auth: str | None = None) -> dict:
    """Notifica al Módulo 2 (Turnos) que se inicia la atención de un turno."""
    if not id_turno_m2:
        return {"status": "ignored", "message": "ID de turno M2 no provisto"}

    if settings.integraciones_mockeadas:
        logger.warning("🧪 [MOCK M2] PATCH /appointments/%s/start", id_turno_m2)
        return {"message": "Appointment started successfully", "mock": True}

    headers = {
        "x-api-key": "appointments-secret-key",
        "Content-Type": "application/json",
    }
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M2_BASE_URL.rstrip('/')}/appointments/{id_turno_m2}/start"
    logger.warning("📡 [M2] Iniciando turno %s en M2: %s", id_turno_m2, url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.patch(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.warning("✅ [M2] Turno %s iniciado exitosamente en M2: %s", id_turno_m2, data)
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M2] Error al iniciar turno %s: %s - %s", id_turno_m2, exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M2 al iniciar turno: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M2] Error de red al conectar con M2: %s", exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 2 (Turnos): {exc}") from exc


async def finalizar_turno(id_turno_m2: int, token_auth: str | None = None) -> dict:
    """Notifica al Módulo 2 (Turnos) que finalizó la atención de un turno."""
    if not id_turno_m2:
        return {"status": "ignored", "message": "ID de turno M2 no provisto"}

    if settings.integraciones_mockeadas:
        logger.warning("🧪 [MOCK M2] PATCH /appointments/%s/finish", id_turno_m2)
        return {
            "message": "Appointment finished successfully",
            "notificationId": "97395c75-ba8a-4205-90e2-61c42a4cab8d",
            "mock": True
        }

    headers = {
        "x-api-key": "appointments-secret-key",
        "Content-Type": "application/json",
    }
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M2_BASE_URL.rstrip('/')}/appointments/{id_turno_m2}/finish"
    logger.warning("📡 [M2] Finalizando turno %s en M2: %s", id_turno_m2, url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.patch(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.warning("✅ [M2] Turno %s finalizado exitosamente en M2: %s", id_turno_m2, data)
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M2] Error al finalizar turno %s: %s - %s", id_turno_m2, exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M2 al finalizar turno: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M2] Error de red al conectar con M2: %s", exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 2 (Turnos): {exc}") from exc
