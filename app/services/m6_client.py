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

    # ── Modo asíncrono vía Core Bus (RabbitMQ) ──
    if settings.ENABLE_CORE_BUS and settings.CORE_EVENT_INTERNACION_SOLICITUD_CREADA_ID > 0:
        from app.integrations.core_bus import publish_named
        from datetime import datetime, timezone

        logger.warning("📡 [M6] Publicando solicitud de internación al bus de eventos (asíncrono)")

        # Mapear prioridad al formato del contrato M6
        prio_map = {
            "baja": "BAJA",
            "media": "MEDIA",
            "alta": "ALTA",
            "emergencia": "URGENTE"
        }
        prioridad_m6 = prio_map.get(str(solicitud.prioridad).lower(), "MEDIA")

        # Determinar tipo del contrato
        tipo_m6 = "TRASLADO" if str(solicitud.tipo).lower() == "pase" else "INTERNACION"

        # Construir payload según contrato en docs/M6_INTEGRACION_M1_HCE(2).md
        payload = {
            "tipo": tipo_m6,
            "solicitud_hce_id": f"HCE-SOL-{solicitud.id_solicitud or 0}",
            "paciente_id": solicitud.id_paciente,
            "medico_solicitante_id": solicitud.medico_solicitante_id or 1,
            "hospital_id": "HOSP-1",
            "observaciones": solicitud.observaciones or solicitud.diagnostico_principal or "",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        if tipo_m6 == "INTERNACION":
            payload.update({
                "origen": "GUARDIA",
                "diagnostico_ingreso": solicitud.diagnostico_principal or "",
                "prioridad": prioridad_m6,
                "episodio_id": solicitud.id_episodio,
                "cama_solicitada_id": solicitud.cama_solicitada_id
            })
        else:
            payload.update({
                "cama_origen_id": 1,  # ID entero fallback requerido por contrato
                "motivo_traslado": solicitud.observaciones or "",
                "cama_destino_solicitada_id": solicitud.cama_destino_solicitada_id
            })

        try:
            res = await publish_named("internacion.solicitud.creada", payload)
            logger.warning("✅ [M6] Solicitud de internación publicada exitosamente en el bus: %s", res)
            return {
                "status": "published",
                "id_solicitud": f"BUS-SOL-{solicitud.id_paciente}",
                "mensaje": "Solicitud de internación publicada en el bus de eventos del Core de forma asíncrona.",
                "bus": True,
            }
        except Exception as exc:
            logger.error("❌ [M6] Error al publicar solicitud de internación en el bus: %s", exc)
            raise RuntimeError(f"No se pudo publicar la solicitud de internación en el bus de eventos: {exc}") from exc

    # ── Modo sincrónico vía HTTP REST ──
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
                "✅ [M6] Solicitud de internación enviada exitosamente a M6 — paciente: %s, evolución: %s",
                solicitud.id_paciente,
                solicitud.id_evolucion_origen,
            )
            return response.json()
        else:
            logger.error(
                "❌ [M6] M6 respondió con error %s al solicitar internación: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"M6 rechazó la solicitud de internación con status {response.status_code}: {response.text}"
            )

    except ImportError:
        # httpx no instalado — se loguea y se simula respuesta en desarrollo
        logger.warning(
            "⚠️ [M6] httpx no disponible. Simulando solicitud de internación a M6 para paciente %s.",
            solicitud.id_paciente,
        )
        return {"status": "simulated", "id_solicitud": None}

    except RuntimeError:
        raise

    except Exception as exc:
        logger.error("❌ [M6] Error de conexión con M6: %s", exc)
        raise RuntimeError(f"No se pudo conectar con el Módulo 6 (Camas): {exc}") from exc
