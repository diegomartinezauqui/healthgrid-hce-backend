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
        "pacienteIdExterno": id_paciente,
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

        url = f"{settings.M7_BASE_URL.rstrip('/')}/integracion/prestaciones"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "billing-secret-key",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.info("📡 [M7] POST %s -> %s", url, payload)
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


async def buscar_prestaciones_nomenclador(
    *,
    codigo: Optional[str] = None,
    descripcion: Optional[str] = None,
    tipo_prestacion: Optional[str] = None,
    token: Optional[str] = None,
) -> list:
    """
    Consultar el nomenclador de M7 (Facturación) para obtener el catálogo de prestaciones.
    """
    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [MOCK M7] GET %s/api/prestaciones-nomenclador — params: %s",
            settings.M7_BASE_URL,
            {"codigo": codigo, "descripcion": descripcion, "tipoPrestacion": tipo_prestacion},
        )
        mock_data = [
            {"id": 1, "codigoNomenclador": "42.01.01", "descripcion": "Consulta médica general", "tipoPrestacion": "CONSULTA", "activa": True},
            {"id": 2, "codigoNomenclador": "99.01.01", "descripcion": "Intervención de especialista", "tipoPrestacion": "PRACTICA", "activa": True},
            {"id": 3, "codigoNomenclador": "01.01.01", "descripcion": "Hemograma completo", "tipoPrestacion": "LABORATORIO", "activa": True},
            {"id": 4, "codigoNomenclador": "02.01.01", "descripcion": "Radiografía de tórax", "tipoPrestacion": "PRACTICA", "activa": True},
        ]
        # Filtrado mock local
        filtered = mock_data
        if codigo:
            filtered = [x for x in filtered if codigo.lower() in x["codigoNomenclador"].lower()]
        if descripcion:
            filtered = [x for x in filtered if descripcion.lower() in x["descripcion"].lower()]
        if tipo_prestacion:
            filtered = [x for x in filtered if x["tipoPrestacion"].upper() == tipo_prestacion.upper()]
        return filtered

    try:
        import httpx

        url = f"{settings.M7_BASE_URL.rstrip('/')}/prestaciones-nomenclador"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "billing-secret-key",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        params = {}
        if codigo:
            params["codigo"] = codigo
        if descripcion:
            params["descripcion"] = descripcion
        if tipo_prestacion:
            params["tipoPrestacion"] = tipo_prestacion

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                "❌ M7 respondió con error %s al buscar prestaciones: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"M7 rechazó la búsqueda con status {response.status_code}: {response.text}"
            )

    except ImportError:
        logger.warning("⚠️ httpx no disponible. Simulando búsqueda en nomenclador.")
        return []

    except RuntimeError:
        raise

    except Exception as exc:
        logger.error("❌ Error de conexión con M7 (Facturación) al buscar nomenclador: %s", exc)
        raise RuntimeError(f"No se pudo conectar con el Módulo 7 (Facturación): {exc}") from exc


async def buscar_entidades_financiadoras(
    *,
    token: Optional[str] = None,
) -> list:
    """
    Consultar las entidades financiadoras (obras sociales / prepagas) registradas en M7.
    """
    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [MOCK M7] GET %s/api/entidades-financiadoras",
            settings.M7_BASE_URL,
        )
        return [
            {"id": 1, "nombre": "OSDE", "cuit": "30-54678912-9", "tipoFinanciador": "PREPAGA", "activa": True},
            {"id": 2, "nombre": "Swiss Medical", "cuit": "30-68951234-8", "tipoFinanciador": "PREPAGA", "activa": True},
            {"id": 3, "nombre": "Particular", "cuit": "", "tipoFinanciador": "OTRO", "activa": True},
            {"id": 4, "nombre": "PAMI", "cuit": "30-50000319-3", "tipoFinanciador": "ESTATAL", "activa": True},
        ]

    try:
        import httpx

        url = f"{settings.M7_BASE_URL.rstrip('/')}/entidades-financiadoras"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "billing-secret-key",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                "❌ M7 respondió con error %s al buscar financiadores: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"M7 rechazó la búsqueda con status {response.status_code}: {response.text}"
            )

    except ImportError:
        logger.warning("⚠️ httpx no disponible. Simulando búsqueda de financiadores.")
        return []

    except RuntimeError:
        raise

    except Exception as exc:
        logger.error("❌ Error de conexión con M7 (Facturación) al buscar financiadores: %s", exc)
        raise RuntimeError(f"No se pudo conectar con el Módulo 7 (Facturación): {exc}") from exc


async def buscar_planes(
    *,
    entidad_financiadora_id: Optional[int] = None,
    token: Optional[str] = None,
) -> list:
    """
    Consultar los planes asociados a entidades financiadoras en M7.
    """
    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [MOCK M7] GET %s/api/planes — params: %s",
            settings.M7_BASE_URL,
            {"entidadFinanciadoraId": entidad_financiadora_id},
        )
        mock_data = [
            {"id": 1, "entidadFinanciadoraId": 1, "entidadFinanciadoraNombre": "OSDE", "nombre": "OSDE 310", "codigo": "310", "activo": True},
            {"id": 2, "entidadFinanciadoraId": 1, "entidadFinanciadoraNombre": "OSDE", "nombre": "OSDE 410", "codigo": "410", "activo": True},
            {"id": 3, "entidadFinanciadoraId": 2, "entidadFinanciadoraNombre": "Swiss Medical", "nombre": "SMG02", "codigo": "SMG02", "activo": True},
            {"id": 4, "entidadFinanciadoraId": 4, "entidadFinanciadoraNombre": "PAMI", "nombre": "Plan Jubilados", "codigo": "PAM-JUB", "activo": True},
        ]
        if entidad_financiadora_id is not None:
            return [x for x in mock_data if x["entidadFinanciadoraId"] == entidad_financiadora_id]
        return mock_data

    try:
        import httpx

        url = f"{settings.M7_BASE_URL.rstrip('/')}/planes"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "billing-secret-key",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        params = {}
        if entidad_financiadora_id is not None:
            params["entidadFinanciadoraId"] = entidad_financiadora_id

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                "❌ M7 respondió con error %s al buscar planes: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"M7 rechazó la búsqueda con status {response.status_code}: {response.text}"
            )

    except ImportError:
        logger.warning("⚠️ httpx no disponible. Simulando búsqueda de planes.")
        return []

    except RuntimeError:
        raise

    except Exception as exc:
        logger.error("❌ Error de conexión con M7 (Facturación) al buscar planes: %s", exc)
        raise RuntimeError(f"No se pudo conectar con el Módulo 7 (Facturación): {exc}") from exc
