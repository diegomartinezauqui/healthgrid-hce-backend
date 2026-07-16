"""
Client hacia el Módulo 5 (Diagnóstico por Imagen).

Dirección y contratos (según lo informado por el grupo de M5):
  - HCE notifica a M5 la creación/modificación de órdenes de imagen.
  - M5 consume nuestra orden vía GET /api/v1/ordenes/{id} (lo hacen ellos).
  - M5 expone, y HCE puede consultar, el detalle del reporte finalizado:
        GET {M5}/v1/webhook/reportById                  -> detalle del reporte
        GET {M5}/v1/webhook/images/{reportId}           -> imágenes del reporte
        GET {M5}/v1/webhook/reports/patientResume       -> resumen del paciente

En INTEGRATION_MODE=mock no se llama a la red: se loguea y se devuelven datos canónicos.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def notificar_orden(
    id_orden: int,
    id_paciente: int,
    descripcion: str | None = None,
    subtipo: str | None = None,
    token_auth: str | None = None,
) -> dict:
    """Avisar a M5 que hay una orden de imagen nueva/modificada para que la procese."""
    payload = {
        "type": "ORDER",
        "id": str(id_orden),
    }
    if settings.integraciones_mockeadas:
        logger.warning("🧪 [MOCK M5] Notificando orden de imagen: %s", payload)
        return {"status": "received", "mock": True, **payload}

    import httpx

    headers = {
        "Content-Type": "application/json",
    }
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M5_BASE_URL.rstrip('/')}/v1/webhook/notifications"
    logger.warning("📡 [M5] Notificando orden a M5: %s", url)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.warning("✅ [M5] Notificación de orden %s enviada con éxito: %s", id_orden, data)
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M5] Error al notificar orden %s: %s - %s", id_orden, exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M5 al notificar orden: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M5] Error de red al conectar con M5: %s", exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 5 (Imágenes): {exc}") from exc


async def obtener_reporte(report_id: str, token: str | None = None) -> dict:
    """Traer el detalle de un reporte de imagen finalizado desde M5."""
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M5] GET /v1/webhook/reportById?reportId=%s", report_id)
        return {
            "reportId": report_id,
            "patientId": "22",
            "title": "Ecografía Renal Bilateral",
            "patientName": "Juan Roman Upamecano",
            "date": "2025-09-05",
            "status": "INTERNACION",
            "techniqueDetail": "Ecografía renal bilateral en proyección PA y lateral izquierda.",
            "techniqueDetails": "Ecografía renal bilateral en proyección PA y lateral izquierda.",
            "observations": "Campos pulmonares libres, sin hallazgos patológicos.",
            "conclusion": "Estudio de tórax sin particularidades.",
            "doctorName": "Dra. Gómez (Radiología)",
            "mock": True,
        }

    import httpx
    headers = {}
    if token:
        headers["Authorization"] = token

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{settings.M5_BASE_URL.rstrip('/')}/v1/webhook/reportById",
            params={"reportId": report_id},
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


async def obtener_imagenes(report_id: str, token: str | None = None) -> dict:
    """Traer el listado de imágenes asociadas a un reporte específico desde M5."""
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M5] GET /v1/webhook/images/reportId?reportId=%s", report_id)
        return {
            "reportId": report_id,
            "images": [
                {
                    "imageId": "838e5688-0c0f-460e-8cb6-86621730da5e",
                    "title": "RMN Columna Lumbar",
                    "creatorName": "Dr. Nicolas Garcia",
                    "date": "2025-02-22",
                    "path": "https://loremflickr.com/400/400?lock=3355484607829747",
                    "image": "https://loremflickr.com/400/400?lock=3355484607829747",
                },
                {
                    "imageId": "ad6746cb-56f7-4ff1-9eb2-3fa4ad3b2359",
                    "title": "Radiografía Lumbar",
                    "creatorName": "Dr. Nicolas Garcia",
                    "date": "2025-04-10",
                    "path": "https://loremflickr.com/400/400?lock=5699819858316477",
                    "image": "https://loremflickr.com/400/400?lock=5699819858316477",
                }
            ]
        }

    import httpx
    headers = {}
    if token:
        headers["Authorization"] = token

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{settings.M5_BASE_URL.rstrip('/')}/v1/webhook/images/reportId",
            params={"reportId": report_id},
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

