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


async def registrar_suscripciones_core():
    """
    Registra dinámicamente las suscripciones HTTP (webhooks) de HCE
    ante el Bus de Eventos del Core.
    Se ejecuta de manera asíncrona al inicio de la aplicación.
    """
    logger.info("⏳ Iniciando registro de suscripciones al bus de Core...")

    # Esperar un momento para asegurar que el servidor HCE esté levantado
    await asyncio.sleep(2.0)

    # 1. Obtener el eventTypeId para laboratorio.resultado_listo (Módulo 4)
    # Por defecto es 5 según documentación, pero intentamos obtenerlo dinámicamente si es posible.
    event_type_id_lab = 5
    try:
        # Nota: URL de integraciones del M4 suministrada en documentación
        lab_integracion_url = "https://modulo-laboratorio-api-production.up.railway.app/v1/integraciones/estado"
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(lab_integracion_url)
            if res.status_code == 200:
                data = res.json()
                event_type_id_lab = data.get("eventTypeId", event_type_id_lab)
                logger.info("🔬 Obtenido eventTypeId %s dinámicamente del Módulo de Laboratorio.", event_type_id_lab)
    except Exception as e:
        logger.warning(
            "⚠️ No se pudo consultar el eventTypeId al Módulo de Laboratorio (%s). Usando ID por defecto: %s",
            e,
            event_type_id_lab
        )

    suscripcion_lab = {
        "event_type_id": event_type_id_lab,
        "subscriber_module": "modulo1",  # M1 es HCE
        "endpoint_url": f"{settings.HCE_PUBLIC_URL}/api/v1/webhook/laboratorio/resultado"
    }

    try:
        url_core = f"{settings.CORE_BASE_URL}/events/subscriptions"
        async with httpx.AsyncClient(timeout=4.0) as client:
            res_core = await client.post(url_core, json=suscripcion_lab)
            if res_core.status_code in (200, 201):
                logger.info("✅ Webhook de Laboratorio registrado en Core con éxito: %s", suscripcion_lab["endpoint_url"])
            else:
                logger.warning(
                    "⚠️ Core rechazó la suscripción de Laboratorio (status %s): %s. Se reintentará en despliegue real.",
                    res_core.status_code,
                    res_core.text
                )
    except Exception as e:
        logger.warning("⚠️ No se pudo conectar con el Core para registrar suscripción de Laboratorio: %s (Core podría estar apagado en desarrollo).", e)
