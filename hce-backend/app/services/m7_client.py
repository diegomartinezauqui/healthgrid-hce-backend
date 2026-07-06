"""
Cliente HTTP para el Módulo 7 (Facturación y Obras Sociales).
HCE llama a M7 cuando se registra un acto médico facturable
(tipo: medicacion, descartable, consulta, procedimiento, etc.).

Dirección: HCE → M7
Tipo: REST sincrónico (fire-and-forget con manejo de error no bloqueante)
Endpoint destino: POST /api/integracion/prestaciones

Contrato acordado con M7 (ver consumos farmacos facturables.txt):
{
    "moduloOrigen":             "HCE",
    "pacienteIdExterno":        str(id_paciente),
    "profesionalIdExterno":     str(id_profesional),
    "planId":                   int,          # id_obra_social de CoberturaMedica
    "codigoPrestacion":         str,          # codigo_nomenclador del ActoMedico
    "numeroAfiliadoInformado":  str | None,   # numero_afiliado de CoberturaMedica
    "fechaAtencion":            ISO-8601,     # fecha_realizacion del ActoMedico
    "cantidad":                 int,
    "idEpisodioExterno":        str(id_episodio),
    "idActoMedicoExterno":      str(id_acto_medico),  # clave de deduplicacion
    "observaciones":            str | None,
}
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def notificar_prestacion(
    *,
    id_paciente: int,
    id_episodio: int,
    id_acto_medico: int,
    id_profesional: int,
    plan_id: int,
    codigo_prestacion: str,
    numero_afiliado: Optional[str],
    fecha_atencion: str,          # ISO-8601
    cantidad: int,
    observaciones: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """
    Notificar a M7 (Facturación) que se registró un acto médico facturable.

    Utiliza `idActoMedicoExterno` como clave de deduplicación para que M7
    pueda evitar facturar el mismo acto dos veces en caso de reintentos.

    Args:
        id_paciente:        ID del paciente en HCE.
        id_episodio:        ID del episodio clínico.
        id_acto_medico:     ID del acto médico recién creado (deduplicación).
        id_profesional:     ID del profesional que realizó el acto.
        plan_id:            ID de obra social / plan (id_obra_social en CoberturaMedica).
        codigo_prestacion:  Código de nomenclador del acto médico.
        numero_afiliado:    Número de afiliado informado por el paciente (puede ser None).
        fecha_atencion:     Fecha/hora del acto en formato ISO-8601.
        cantidad:           Cantidad de unidades del acto.
        observaciones:      Texto libre (ej. "Medicamento dispensado asociado a receta 8502").
        token:              JWT del llamador para reenviar en modo live (opcional).

    Returns:
        Respuesta JSON de M7 (o respuesta mock en modo mock).

    Raises:
        RuntimeError: Si M7 devuelve un error HTTP o no está disponible (modo live).
    """
    payload = {
        "moduloOrigen": "HCE",
        "pacienteIdExterno": str(id_paciente),
        "profesionalIdExterno": str(id_profesional),
        "planId": plan_id,
        "codigoPrestacion": codigo_prestacion,
        "numeroAfiliadoInformado": numero_afiliado,
        "fechaAtencion": fecha_atencion,
        "cantidad": cantidad,
        "idEpisodioExterno": str(id_episodio),
        "idActoMedicoExterno": str(id_acto_medico),
        "observaciones": observaciones,
    }

    # ── Modo mock: loguear intención, no hacer HTTP ──────────────────────────
    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [MOCK M7] POST %s/api/integracion/prestaciones → %s",
            settings.M7_BASE_URL,
            payload,
        )
        return {
            "status": "received",
            "idPrestacion": f"MOCK-PREST-{id_acto_medico}",
            "mensaje": "Prestación registrada en M7 (mock). Lista para facturación.",
            "mock": True,
            **payload,
        }

    # ── Modo live: llamada HTTP real a M7 ────────────────────────────────────
    try:
        import httpx

        url = f"{settings.M7_BASE_URL}/api/integracion/prestaciones"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code in (200, 201):
            logger.info(
                "✅ Prestación notificada a M7 — paciente: %s, acto: %s, código: %s",
                id_paciente,
                id_acto_medico,
                codigo_prestacion,
            )
            return response.json()
        else:
            logger.error(
                "❌ M7 respondió con error %s al registrar prestación: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"M7 rechazó la prestación con status {response.status_code}: {response.text}"
            )

    except ImportError:
        logger.warning(
            "⚠️ httpx no disponible. Simulando notificación a M7 para acto %s.",
            id_acto_medico,
        )
        return {"status": "simulated", "idPrestacion": None}

    except RuntimeError:
        raise

    except Exception as exc:
        logger.error("❌ Error de conexión con M7 (Facturación): %s", exc)
        raise RuntimeError(f"No se pudo conectar con el Módulo 7 (Facturación): {exc}") from exc
