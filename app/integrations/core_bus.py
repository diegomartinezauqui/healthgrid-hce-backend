"""
Cliente del bus de eventos del Core (M10) — modelo real:

  - Se CONFIGURA y se PUBLICA llamando al Core por HTTP.
  - Se ESCUCHA por RabbitMQ (ver `rabbit_consumer.py`).

Este módulo cubre la parte HTTP: login al Core, publicación de eventos
(`POST /events/log`, con el payload como STRING) y el provisioning de colas,
eventos y bindings (usado por `scripts/setup_core_bus.py`).

Todo está gateado: si `ENABLE_CORE_BUS` es False, se loguea y no se hace red.
"""

import json
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_token_cache: dict = {"token": None}


async def _get_core_token(client: httpx.AsyncClient) -> Optional[str]:
    """Login al Core con la cuenta de servicio de HCE. Cachea el token."""
    if _token_cache["token"]:
        return _token_cache["token"]
    if not settings.CORE_SERVICE_EMAIL or not settings.CORE_SERVICE_PASSWORD:
        logger.warning("⚠️ Faltan CORE_SERVICE_EMAIL/PASSWORD; no se puede autenticar al Core.")
        return None
    resp = await client.post(
        f"{settings.CORE_API_URL}/auth/login",
        json={"email": settings.CORE_SERVICE_EMAIL, "password": settings.CORE_SERVICE_PASSWORD},
    )
    resp.raise_for_status()
    token = resp.json().get("token") or resp.json().get("access_token")
    _token_cache["token"] = token
    return token


async def _auth_headers(client: httpx.AsyncClient) -> dict:
    token = await _get_core_token(client)
    return {"Authorization": f"Bearer {token}"} if token else {}


async def publish_event(
    event_type_id: int,
    payload: dict,
    correlation_id: Optional[str] = None,
    publisher_module: str = "hce",
) -> dict:
    """
    Publica un evento al Core (`POST /events/log`). El `payload` viaja como STRING.
    Si se espera respuesta, incluir `correlation_id` (y `response_event_id` dentro
    del payload). Gateado por ENABLE_CORE_BUS.
    """
    cuerpo = dict(payload)
    if correlation_id:
        cuerpo["correlation_id"] = correlation_id

    if not settings.ENABLE_CORE_BUS:
        logger.info(
            "🧪 [MOCK Core bus] publish_event type=%s publisher=%s payload=%s",
            event_type_id, publisher_module, cuerpo,
        )
        return {"status": "mock", "event_type_id": event_type_id, "payload": cuerpo}

    async with httpx.AsyncClient(timeout=8.0) as client:
        headers = await _auth_headers(client)
        resp = await client.post(
            f"{settings.CORE_API_URL}/events/log",
            headers=headers,
            json={
                "event_type_id": event_type_id,
                "publisher_module": publisher_module,
                "payload": json.dumps(cuerpo, ensure_ascii=False),  # el Core espera string
            },
        )
        resp.raise_for_status()
        logger.info("📤 Evento publicado al Core (type=%s).", event_type_id)
        return resp.json()


def _event_id_por_nombre(nombre: str) -> int:
    """Mapea un nombre lógico de evento al event_type_id configurado (0 = sin configurar)."""
    return {
        "orden.creada": settings.CORE_EVENT_ORDEN_CREADA_ID,
        "receta.creada": settings.CORE_EVENT_RECETA_CREADA_ID,
        "episodio.cerrado": settings.CORE_EVENT_EPISODIO_CERRADO_ID,
        "notificacion.obligatoria": settings.CORE_EVENT_PATOLOGIA_CRITICA_ID,
        # Evento de M6 — resolucion de solicitud de cama (aprobada o rechazada)
        "solicitud.resuelta": settings.CORE_EVENT_SOLICITUD_RESUELTA_ID,
    }.get(nombre, 0)


async def publish_named(nombre: str, payload: dict, correlation_id: Optional[str] = None) -> Optional[dict]:
    """
    Publica un evento lógico de HCE si su event_type_id está configurado.
    No-op (log) si el id es 0 o el bus está apagado. Pensado para llamarse desde
    los services sin acoplarlos a ids concretos.
    """
    event_type_id = _event_id_por_nombre(nombre)
    if not event_type_id:
        logger.info("ℹ️ [Core bus] '%s' sin event_type_id configurado; no se publica.", nombre)
        return None
    return await publish_event(event_type_id, payload, correlation_id=correlation_id)


# ─── Provisioning (usado por scripts/setup_core_bus.py) ───────────

async def create_queue(client: httpx.AsyncClient, queue_name: str, queue_type: str) -> dict:
    """queue_type: 'requests' | 'responses'. El Core agrega el sufijo y la DLQ."""
    headers = await _auth_headers(client)
    resp = await client.post(
        f"{settings.CORE_API_URL}/rabbit/queues",
        headers=headers,
        json={"queue_name": queue_name, "queue_type": queue_type},
    )
    resp.raise_for_status()
    return resp.json()


async def create_event(client: httpx.AsyncClient, name: str, description: str, source_module: str) -> dict:
    headers = await _auth_headers(client)
    resp = await client.post(
        f"{settings.CORE_API_URL}/events/types",
        headers=headers,
        json={"name": name, "description": description, "source_module": source_module},
    )
    resp.raise_for_status()
    return resp.json()


async def create_binding(client: httpx.AsyncClient, event_id: int, queue_name: str) -> dict:
    headers = await _auth_headers(client)
    resp = await client.post(
        f"{settings.CORE_API_URL}/rabbit/bindings",
        headers=headers,
        json={"event_id": event_id, "queue_name": queue_name},
    )
    resp.raise_for_status()
    return resp.json()
