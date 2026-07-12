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
    medico_id: int,
    estudio_ids: List[int],
    prioridad: str,
    origen: str = "HCE",
) -> dict:
    """
    Notifica la creación de una orden médica de laboratorio a M4 (POST /v1/ordenes).
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
        logger.info("🧪 [MOCK M4] POST /v1/ordenes -> %s", payload)
        return {
            "status": "success",
            "message": "Orden de laboratorio notificada (mock).",
            "id": 100 + id_orden,
            "mock": True,
            **payload,
        }

    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{settings.M4_BASE_URL}/v1/ordenes", json=payload)
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
