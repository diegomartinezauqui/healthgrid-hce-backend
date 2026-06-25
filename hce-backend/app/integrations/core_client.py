"""
Client hacia el Core (M10) — bus de eventos por suscripción HTTP.

El Core actúa como broker: HCE se suscribe a un tipo de evento indicando una
URL de webhook, y el Core hace POST a esa URL cuando el evento ocurre.
Así es como M4 (Laboratorio) nos hace llegar `laboratorio.resultado_listo`.

Endpoints reales del Core (según lo informado por los grupos):
  GET  {CORE}/events/types                 -> lista de tipos de evento + ids
  POST {CORE}/events/subscriptions         -> crear suscripción

En INTEGRATION_MODE=mock no se llama a la red: se loguea y se devuelve una
respuesta canónica.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

SUBSCRIBER_MODULE = "modulo1_hce"


async def listar_tipos_evento() -> list[dict]:
    """Obtener los tipos de evento expuestos por el Core."""
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK Core] GET /events/types")
        return [
            {"id": 5, "evento": "laboratorio.resultado_listo", "modulo": "modulo4"},
            {"id": 7, "evento": "imagenes.reporte_finalizado", "modulo": "modulo5"},
            {"id": 3, "evento": "turnos.presentismo", "modulo": "modulo2"},
        ]

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.CORE_BASE_URL}/events/types")
        resp.raise_for_status()
        return resp.json()


async def suscribir_evento(event_type_id: int, endpoint_url: str) -> dict:
    """
    Registrar una suscripción en el Core para que reenvíe el evento a nuestro webhook.

    Args:
        event_type_id: id del tipo de evento en el Core (p.ej. 5 = laboratorio.resultado_listo).
        endpoint_url: URL pública de nuestro webhook que recibirá el POST del Core.
    """
    payload = {
        "event_type_id": event_type_id,
        "subscriber_module": SUBSCRIBER_MODULE,
        "endpoint_url": endpoint_url,
    }

    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK Core] POST /events/subscriptions %s", payload)
        return {"status": "subscribed", "subscription_id": f"MOCK-SUB-{event_type_id}", **payload}

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{settings.CORE_BASE_URL}/events/subscriptions", json=payload)
        resp.raise_for_status()
        return resp.json()
