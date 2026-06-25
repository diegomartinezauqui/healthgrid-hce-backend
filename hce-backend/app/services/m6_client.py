"""
Cliente HTTP para el Módulo 6 (Camas).
HCE llama a M6 cuando un médico indica la necesidad de internar a un paciente.

Dirección: HCE → M6
Tipo: REST sincrónico
Endpoint destino: POST /api/M6/solicitudes-internacion
"""

import logging
from typing import Optional

from app.config import settings
from app.schemas.internacion import SolicitudInternacionRequest

logger = logging.getLogger(__name__)


async def solicitar_internacion(
    solicitud: SolicitudInternacionRequest,
    token: Optional[str] = None,
) -> dict:
    """
    Enviar una solicitud de internación al Módulo 6 (Camas).

    HCE llama a este cliente cuando un médico registra en la evolución
    la necesidad de internar a un paciente. M6 gestiona la asignación
    de cama y, una vez asignada, notifica de vuelta a HCE mediante
    POST /internacion/ingreso.

    Args:
        solicitud: Payload con los datos del paciente y la internación requerida.
        token: JWT del service account de HCE (opcional en desarrollo).

    Returns:
        Respuesta JSON de M6 con el id de la solicitud creada.

    Raises:
        RuntimeError: Si M6 devuelve un error HTTP o no está disponible.
    """
    # ── Modo integración mockeada: no se llama a M6 real ──
    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [MOCK M6] Solicitud de internación simulada — paciente: %s, sector: %s, prioridad: %s",
            solicitud.id_paciente,
            solicitud.sector_solicitado,
            solicitud.prioridad,
        )
        return {
            "status": "accepted",
            "id_solicitud": f"MOCK-SOL-{solicitud.id_paciente}",
            "mensaje": "Solicitud recibida por M6 (mock). Se notificará el ingreso vía POST /internacion/ingreso.",
            "mock": True,
        }

    try:
        import httpx

        url = f"{settings.M6_BASE_URL}/M6/solicitudes-internacion"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=solicitud.model_dump(mode="json"),
                headers=headers,
            )

        if response.status_code in (200, 201):
            logger.info(
                "✅ Solicitud de internación enviada a M6 — paciente: %s, evolución: %s",
                solicitud.id_paciente,
                solicitud.id_evolucion_origen,
            )
            return response.json()
        else:
            logger.error(
                "❌ M6 respondió con error %s al solicitar internación: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"M6 rechazó la solicitud de internación con status {response.status_code}: {response.text}"
            )

    except ImportError:
        # httpx no instalado — se loguea y se simula respuesta en desarrollo
        logger.warning(
            "⚠️ httpx no disponible. Simulando solicitud de internación a M6 para paciente %s.",
            solicitud.id_paciente,
        )
        return {"status": "simulated", "id_solicitud": None}

    except RuntimeError:
        raise

    except Exception as exc:
        logger.error("❌ Error de conexión con M6: %s", exc)
        raise RuntimeError(f"No se pudo conectar con el Módulo 6 (Camas): {exc}") from exc
