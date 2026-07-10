"""Schemas de solicitudes de cama (internación / pase) — integración M6."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SolicitudCamaCreate(BaseModel):
    """Body para crear una solicitud de internación o pase de cama."""

    tipo: Literal["internacion", "pase"] = Field("internacion", examples=["internacion"])
    prioridad: Literal["Baja", "Media", "Alta"] = Field("Media", examples=["Alta"])
    sector: Optional[str] = Field(None, examples=["UTI — Unidad de Terapia Intensiva"])
    motivo: Optional[str] = Field(None, examples=["Requiere monitoreo intensivo."])


class SolicitudCamaResolver(BaseModel):
    """Body para simular la respuesta de M6 sobre una solicitud pendiente."""

    decision: Literal["aceptada", "rechazada"] = Field(..., examples=["aceptada"])
    cama: Optional[str] = Field(None, examples=["Cama 4"])
    habitacion: Optional[str] = Field(None, examples=["Hab 201"])
    motivo_rechazo: Optional[str] = Field(None, examples=["No hay camas disponibles en el sector."])


class SolicitudCamaSchema(BaseModel):
    """Respuesta de una solicitud de cama."""

    id_solicitud: int
    id_paciente: int
    id_episodio: int
    tipo: str
    prioridad: str
    sector: Optional[str] = None
    motivo: Optional[str] = None
    estado: str
    cama: Optional[str] = None
    habitacion: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    fecha_solicitud: Optional[datetime] = None
    fecha_resolucion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CamaActual(BaseModel):
    """Ubicación actual del paciente internado (último movimiento)."""

    sector: Optional[str] = None
    habitacion: Optional[str] = None
    cama: Optional[str] = None
    fecha_ingreso: Optional[datetime] = None


class SolicitudCamaListResponse(BaseModel):
    """Listado de solicitudes de un episodio + la cama actual del paciente."""

    solicitudes: List[SolicitudCamaSchema] = Field(default_factory=list)
    cama_actual: Optional[CamaActual] = None
    internado: bool = False
