"""Schemas de internación (Integración M6 Camas)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from common.enums.enums_internacion import PrioridadInternacion, SectorSolicitado


class IngresoInternacionRequest(BaseModel):
    """Payload enviado por M6 para notificar ingreso de paciente a cama."""

    id_paciente: int = Field(..., examples=[10500])
    sector: str = Field(..., examples=["UTI"])
    habitacion: Optional[str] = Field(None, examples=["Terapia A"])
    cama: str = Field(..., examples=["Cama 4"])
    fecha_ingreso: datetime = Field(..., examples=["2026-04-17T14:30:00Z"])
    medico_solicitante: Optional[str] = Field(None, examples=["Dr. Pérez"])


class SolicitudInternacionRequest(BaseModel):
    """Payload enviado por HCE hacia M6 para solicitar internación."""

    id_paciente: int = Field(..., examples=[10500])
    id_evolucion_origen: int = Field(..., examples=[302])
    prioridad: PrioridadInternacion = Field(..., examples=["Alta"])
    sector_solicitado: SectorSolicitado = Field(..., examples=["UTI"])
    diagnostico_principal: Optional[str] = Field(
        None, examples=["Insuficiencia respiratoria aguda"]
    )
    observaciones: Optional[str] = Field(
        None, examples=["Paciente requiere asistencia respiratoria mecánica inmediata."]
    )


class IngresoInternacionResponse(BaseModel):
    """Respuesta tras crear episodio de internación."""

    status: str = Field(default="success", examples=["success"])
    mensaje: str = Field(
        default="Episodio creado y cama asignada correctamente.",
        examples=["Episodio creado y cama asignada correctamente."],
    )
    data: Optional[dict] = Field(
        None, examples=[{"id_episodio": 700, "id_movimiento": 1}]
    )
