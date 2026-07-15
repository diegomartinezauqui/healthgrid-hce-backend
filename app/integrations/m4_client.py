"""
Cliente HTTP para el Módulo 4 (Laboratorio).
HCE llama a M4 para registrar órdenes clínicas y consultar estudios disponibles.
"""

import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def notificar_orden_laboratorio(
    id_orden: int,
    id_paciente: int,
    paciente_nombre: str,
    paciente_dni: str,
    paciente_edad: int,
    paciente_sexo: str,
    prioridad: str,
    origen: str = "HCE",
    descripcion_pedido: str | None = None,
    token_auth: str | None = None,
    alertas_clinicas: list[dict] | None = None,
) -> dict:
    """
    Notifica la creación de una orden médica de laboratorio a M4 (POST /v1/ordenes/hce).
    """
    prioridad_m4 = "Routine"
    prioridad_normalizada = str(prioridad).lower()
    if prioridad_normalizada == "urgente":
        prioridad_m4 = "STAT"
    elif prioridad_normalizada == "emergencia":
        prioridad_m4 = "Emergencia"

    payload = {
        "idOrden": id_orden,
        "idPaciente": id_paciente,
        "descripcionPedido": descripcion_pedido,
        "prioridad": prioridad_m4,
        "alertasClinicas": alertas_clinicas or [],
        "pacienteNombre": paciente_nombre,
        "pacienteDni": paciente_dni,
        "pacienteEdad": paciente_edad,
        "pacienteSexo": paciente_sexo,
    }

    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] POST /v1/ordenes/hce -> %s", payload)
        return {
            "status": "success",
            "message": "Orden de laboratorio notificada (mock).",
            "id": 100 + id_orden,
            "mock": True,
            **payload,
        }

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"Content-Type": "application/json"}
        if token_auth:
            headers["Authorization"] = token_auth

        resp = await client.post(
            f"{settings.M4_BASE_URL.rstrip('/')}/v1/ordenes/hce",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


async def obtener_estudios() -> List[dict]:
    """
    Obtiene el catálogo de estudios disponibles en el Módulo 4 (GET /v1/estudios).
    """
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] GET /v1/estudios")
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
                        "rangosReferencia": [
                            {
                                "id": 1,
                                "valorMinimo": 12.0,
                                "valorMaximo": 16.0,
                                "sexo": "Femenino",
                                "edadMinima": 18,
                                "edadMaxima": 120,
                                "limiteCriticoInferior": 7.0,
                                "limiteCriticoSuperior": 20.0,
                            }
                        ],
                    }
                ],
            }
        ]

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.M4_BASE_URL}/v1/estudios")
        resp.raise_for_status()
        return resp.json()


async def obtener_analitos(categoria: str | None = None) -> List[dict]:
    """
    Obtiene el catálogo de analitos disponibles en el Módulo 4 (GET /v1/analitos).
    Permite filtrar opcionalmente por categoría.
    """
    if settings.integraciones_mockeadas:
        logger.info("🧪 [MOCK M4] GET /v1/analitos categoria=%s", categoria)
        analitos = [
            {
                "id": 101,
                "codigo": "GLU",
                "nombre": "Glucosa",
                "unidadMedida": "mg/dL",
                "categoria": "Bioquímica",
                "metodo": "Enzimático",
                "rangosReferencia": [
                    {
                        "id": 1,
                        "valorMinimo": 70.0,
                        "valorMaximo": 100.0,
                        "sexo": None,
                        "edadMinima": 0,
                        "edadMaxima": 120,
                        "limiteCriticoInferior": 50.0,
                        "limiteCriticoSuperior": 500.0,
                    }
                ],
            },
            {
                "id": 102,
                "codigo": "HEM",
                "nombre": "Hemoglobina",
                "unidadMedida": "g/dL",
                "categoria": "Hematología",
                "metodo": "Espectrofotometría",
                "rangosReferencia": [
                    {
                        "id": 2,
                        "valorMinimo": 12.0,
                        "valorMaximo": 16.0,
                        "sexo": "Femenino",
                        "edadMinima": 18,
                        "edadMaxima": 120,
                        "limiteCriticoInferior": 7.0,
                        "limiteCriticoSuperior": 20.0,
                    }
                ],
            },
        ]
        if categoria:
            categoria_normalizada = categoria.strip().lower()
            return [a for a in analitos if str(a.get("categoria", "")).lower() == categoria_normalizada]
        return analitos

    import httpx

    params = {"categoria": categoria} if categoria else None
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.M4_BASE_URL}/v1/analitos", params=params)
        resp.raise_for_status()
        return resp.json()


async def obtener_ordenes(query_params: dict) -> dict:
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

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.M4_BASE_URL}/v1/ordenes", params=query_params)
        resp.raise_for_status()
        return resp.json()
