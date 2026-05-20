"""Schemas de alertas clínicas del paciente."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from common.enums.enums_alertas import EstadoAlerta, SeveridadAlerta, TipoConsideracion


class AlertaCreate(BaseModel):
    """Body para crear una nueva alerta clínica."""

    tipo: TipoConsideracion = Field(..., examples=["Alergia"])
    severidad: SeveridadAlerta = Field(..., examples=["Severa"])
    descripcion: str = Field(..., examples=["Alergia severa a penicilina y derivados."])


class AlertaUpdate(BaseModel):
    """Body para resolver una alerta clínica (PATCH)."""

    estado: EstadoAlerta = Field(..., examples=["Resuelta"])
    motivo_resolucion: str = Field(..., examples=["Alergia superada, confirmado por alergista."])


class AlertaSchema(BaseModel):
    """Respuesta completa de una alerta clínica."""

    id: int
    id_paciente: int
    tipo: TipoConsideracion
    severidad: SeveridadAlerta
    descripcion: str
    estado: EstadoAlerta
    fecha_registro: datetime
    id_medico_registro: int
    fecha_resolucion: Optional[datetime] = None
    id_medico_resolucion: Optional[int] = None
    motivo_resolucion: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertaSmartPayload(BaseModel):
    """
    Schema reducido para Smart Payload en órdenes y recetas.
    Solo incluye lo necesario para que M3/M4/M5 tomen decisiones clínicas.
    """

    tipo: TipoConsideracion
    severidad: SeveridadAlerta
    descripcion: str

    model_config = {"from_attributes": True}
