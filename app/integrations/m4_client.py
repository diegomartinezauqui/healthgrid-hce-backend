"""
Cliente HTTP para el Módulo 4 (Laboratorio).
HCE llama a M4 para registrar órdenes clínicas y consultar analitos/estudios disponibles.

Endpoints activos del contrato con M4:
  GET  /v1/analitos          → catálogo de analitos (con filtro opcional ?categoria=)
  POST /v1/ordenes/hce       → ingesta de orden desde HCE (idempotente por idOrdenHce)
"""

import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def _resolver_nombres_estudios(
    estudio_ids: List[int],
    headers: dict,
) -> str:
    """
    Consulta GET /v1/estudios de M4 y devuelve los nombres de los estudios
    correspondientes a `estudio_ids`, concatenados con ' / '.
    M4 prefiere un estudio por orden; si se envían varios se concatenan como fallback.
    Si falla la consulta, devuelve una cadena vacía.
    """
    import httpx
    url = f"{settings.M4_BASE_URL.rstrip('/')}/v1/estudios"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            estudios: list = resp.json()
        # estudios es una lista de objetos con al menos {"id": ..., "nombre": ...}
        id_set = set(estudio_ids)
        nombres = [
            e.get("nombre", str(e.get("id", "")))
            for e in estudios
            if e.get("id") in id_set
        ]
        if nombres:
            return " / ".join(nombres)
        # Si M4 devuelve objetos con clave distinta, intentamos 'name'
        nombres_alt = [
            e.get("name", str(e.get("id", "")))
            for e in estudios
            if e.get("id") in id_set
        ]
        return " / ".join(nombres_alt) if nombres_alt else ""
    except Exception as exc:
        logger.warning("⚠️ [M4] No se pudo obtener nombres de estudios: %s", exc)
        return ""


async def notificar_orden_hce(
    id_orden: int,
    id_paciente: int,
    descripcion_pedido: Optional[str],
    prioridad: str,
    paciente_nombre: str,
    paciente_dni: str,
    paciente_edad: int,
    paciente_sexo: str,
    alertas_clinicas: Optional[List[dict]] = None,
    estudio_ids: Optional[List[int]] = None,
    token_auth: Optional[str] = None,
) -> dict:
    """
    Envía una orden de laboratorio a M4 usando el nuevo endpoint
    POST /v1/ordenes/hce (idempotente: M4 ignora duplicados por idOrdenHce).

    El campo `descripcionPedido` se construye así (en orden de prioridad):
      1. Nombre(s) del/los estudio(s) obtenidos desde GET /v1/estudios de M4
         (concatenados con ' / ' si hay más de uno, aunque M4 prefiere uno solo).
      2. `descripcion_pedido` enviado por el médico como texto libre.
      3. Cadena vacía como último fallback.
    """
    import httpx
    headers: dict = {}
    if token_auth:
        headers["Authorization"] = token_auth

    # ── Resolver descripción a partir de los estudios de M4 ──────────────
    descripcion_final = descripcion_pedido or ""

    if settings.integraciones_mockeadas:
        # En modo mock simplemente usamos los IDs como representación
        if estudio_ids:
            descripcion_final = descripcion_pedido or f"Estudio(s) ID: {', '.join(map(str, estudio_ids))}"
        payload = {
            "idOrden": id_orden,
            "idPaciente": id_paciente,
            "descripcionPedido": descripcion_final,
            "prioridad": prioridad,
            "alertasClinicas": alertas_clinicas or [],
            "pacienteNombre": paciente_nombre,
            "pacienteDni": paciente_dni,
            "pacienteEdad": paciente_edad,
            "pacienteSexo": paciente_sexo,
            "estudioIds": estudio_ids or [],
        }
        logger.info("🧪 [MOCK M4] POST /v1/ordenes/hce -> %s", payload)
        return {
            "status": "success",
            "message": "Orden HCE notificada a M4 (mock).",
            "idOrden": id_orden,
            "mock": True,
        }

    # Modo live: consultar los nombres reales de los estudios en M4
    if estudio_ids:
        nombres_estudios = await _resolver_nombres_estudios(estudio_ids, headers)
        if nombres_estudios:
            descripcion_final = nombres_estudios
            logger.info(
                "📋 [M4] Descripción de orden %s construida desde GET /v1/estudios: '%s'",
                id_orden,
                descripcion_final,
            )
        else:
            logger.warning(
                "⚠️ [M4] No se obtuvieron nombres de estudios para IDs %s; usando descripción manual: '%s'",
                estudio_ids,
                descripcion_final,
            )

    payload = {
        "idOrden": id_orden,
        "idPaciente": id_paciente,
        "descripcionPedido": descripcion_final,
        "prioridad": prioridad,
        "alertasClinicas": alertas_clinicas or [],
        "pacienteNombre": paciente_nombre,
        "pacienteDni": paciente_dni,
        "pacienteEdad": paciente_edad,
        "pacienteSexo": paciente_sexo,
        "estudioIds": estudio_ids or [],
    }

    url = f"{settings.M4_BASE_URL.rstrip('/')}/v1/ordenes/hce"
    logger.info("📡 [M4] Notificando orden %s a M4: %s", id_orden, url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("✅ [M4] Orden %s notificada exitosamente a M4: %s", id_orden, data)
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M4] Error HTTP al notificar orden %s a M4: %s - %s", id_orden, exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M4 al notificar orden: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M4] Error de red al notificar orden %s a M4: %s", id_orden, exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 4 (Laboratorio): {exc}") from exc


async def notificar_orden_laboratorio(
    id_orden: int,
    id_paciente: int,
    paciente_nombre: str,
    paciente_dni: str,
    paciente_edad: int,
    paciente_sexo: str,
    medico_id: int,
    estudio_ids: List[int],
    prioridad: str,
    origen: str = "HCE",
    token_auth: Optional[str] = None,
) -> dict:
    """
    [LEGADO] Notifica a M4 vía POST /v1/ordenes (endpoint anterior).
    Usar notificar_orden_hce() para el nuevo contrato.
    """
    prio_val = 0
    if str(prioridad).lower() == "urgente":
        prio_val = 1
    elif str(prioridad).lower() == "emergencia":
        prio_val = 2

    payload = {
        "pacienteId": id_paciente,
        "pacienteNombre": paciente_nombre,
        "pacienteDni": paciente_dni,
        "pacienteEdad": paciente_edad,
        "pacienteSexo": paciente_sexo,
        "medicoId": medico_id,
        "estudioIds": estudio_ids,
        "prioridad": prio_val,
        "origen": origen
    }

    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] POST /v1/ordenes (legado) -> %s", payload)
        return {
            "status": "success",
            "message": "Orden de laboratorio notificada (mock).",
            "id": 100 + id_orden,
            "mock": True,
            **payload,
        }

    import httpx
    headers = {}
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M4_BASE_URL.rstrip('/')}/v1/ordenes"
    logger.info("📡 [M4] Notificando orden legada %s a M4: %s", id_orden, url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("✅ [M4] Orden legada %s notificada exitosamente a M4: %s", id_orden, data)
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M4] Error HTTP al notificar orden legada %s a M4: %s - %s", id_orden, exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M4 al notificar orden: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M4] Error de red al notificar orden legada %s a M4: %s", id_orden, exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 4 (Laboratorio): {exc}") from exc


async def obtener_analitos(
    categoria: Optional[str] = None,
    token_auth: Optional[str] = None,
) -> List[dict]:
    """
    Obtiene el catálogo de analitos disponibles en M4 (GET /v1/analitos).
    Filtra opcionalmente por categoría: "Hematologia", "Bioquimica", "Orina", etc.
    """
    params = {}
    if categoria:
        params["categoria"] = categoria

    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] GET /v1/analitos params=%s", params)
        mock_data = [
            {
                "id": 1,
                "codigo": "HB",
                "nombre": "Hemoglobina",
                "unidadMedida": "g/dL",
                "categoria": "Hematologia",
                "metodo": "Espectrofotometría",
            },
            {
                "id": 2,
                "codigo": "GLU",
                "nombre": "Glucosa",
                "unidadMedida": "mg/dL",
                "categoria": "Bioquimica",
                "metodo": "Enzimático colorimétrico",
            },
            {
                "id": 3,
                "codigo": "CREAT",
                "nombre": "Creatinina",
                "unidadMedida": "mg/dL",
                "categoria": "Bioquimica",
                "metodo": "Jaffé",
            },
            {
                "id": 4,
                "codigo": "SED",
                "nombre": "Sedimento urinario",
                "unidadMedida": "/campo",
                "categoria": "Orina",
                "metodo": "Microscopia",
            },
            {
                "id": 5,
                "codigo": "HTO",
                "nombre": "Hematocrito",
                "unidadMedida": "%",
                "categoria": "Hematologia",
                "metodo": "Centrífuga",
            },
        ]
        if categoria:
            mock_data = [a for a in mock_data if a["categoria"].lower() == categoria.lower()]
        return mock_data

    import httpx
    headers = {}
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M4_BASE_URL.rstrip('/')}/v1/analitos"
    logger.info("📡 [M4] Obteniendo analitos de M4: %s", url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("✅ [M4] Analitos obtenidos exitosamente de M4: %s items", len(data))
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M4] Error HTTP al obtener analitos de M4: %s - %s", exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M4 al obtener analitos: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M4] Error de red al obtener analitos de M4: %s", exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 4 (Laboratorio): {exc}") from exc


async def obtener_estudios(token_auth: Optional[str] = None) -> List[dict]:
    """
    [LEGADO] Obtiene el catálogo de estudios en M4 (GET /v1/estudios).
    Usar obtener_analitos() para el nuevo contrato.
    """
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] GET /v1/estudios (legado)")
        return [
            {
                "id": 1,
                "nombre": "Hemograma completo",
                "descripcion": "Estudio cuantitativo y cualitativo de células sanguíneas.",
                "analitos": [
                    {
                        "id": 101,
                        "codigo": "HEM",
                        "nombre": "Hemoglobina",
                        "unidadMedida": "g/dL",
                        "categoria": "Sanguíneo",
                        "metodo": "Espectrofotometría",
                    }
                ],
            }
        ]

    import httpx
    headers = {}
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M4_BASE_URL.rstrip('/')}/v1/estudios"
    logger.info("📡 [M4] Obteniendo estudios (legado) de M4: %s", url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("✅ [M4] Estudios (legado) obtenidos exitosamente de M4: %s items", len(data))
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M4] Error HTTP al obtener estudios (legado) de M4: %s - %s", exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M4 al obtener estudios: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M4] Error de red al obtener estudios (legado) de M4: %s", exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 4 (Laboratorio): {exc}") from exc


async def obtener_ordenes(query_params: dict, token_auth: Optional[str] = None) -> dict:
    """
    Obtiene las órdenes registradas en M4 (GET /v1/ordenes).
    Soporta envío de parámetros de consulta para filtrado.
    """
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] GET /v1/ordenes con params: %s", query_params)
        return {
            "id": 1,
            "pacienteId": query_params.get("pacienteId", 1),
            "pacienteNombre": "Juan Pérez",
            "pacienteDni": "12345678",
            "pacienteEdad": 35,
            "pacienteSexo": "M",
            "medicoId": 101,
            "fechaSolicitud": "2026-06-25T20:09:53.032Z",
            "estado": "Pendiente",
            "prioridad": "Normal",
            "origen": "HCE",
            "estudiosSolicitados": [],
            "resultados": [],
        }

    import httpx
    headers = {}
    if token_auth:
        headers["Authorization"] = token_auth

    url = f"{settings.M4_BASE_URL.rstrip('/')}/v1/ordenes"
    logger.info("📡 [M4] Obteniendo órdenes de M4: %s con params %s", url, query_params)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=query_params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("✅ [M4] Órdenes obtenidas exitosamente de M4")
            return data
        except httpx.HTTPStatusError as exc:
            logger.error("❌ [M4] Error HTTP al obtener órdenes de M4: %s - %s", exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Error de M4 al obtener órdenes: {exc.response.text}") from exc
        except Exception as exc:
            logger.error("❌ [M4] Error de red al obtener órdenes de M4: %s", exc)
            raise RuntimeError(f"No se pudo conectar con el Módulo 4 (Laboratorio): {exc}") from exc
