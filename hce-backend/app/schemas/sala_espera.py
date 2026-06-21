"""Schemas para la Sala de Espera."""

from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field

from common.enums.enums_sala_espera import EstadoSalaEspera


class SalaEsperaCreate(BaseModel):
    """Payload para registrar el ingreso a la sala de espera."""

    id_paciente: int = Field(..., examples=[10500])
    id_medico: int = Field(
        ...,
        validation_alias=AliasChoices("id_profesional", "id_medico"),
        examples=[42],
    )
    id_sede: int = Field(..., examples=[3])
    id_turno_m2: Optional[int] = Field(None, examples=[88402])
    fecha_turno: Optional[datetime] = Field(None, examples=["2026-06-19T10:00:00Z"])
    fecha_llegada: Optional[datetime] = Field(None, examples=["2026-06-21T09:45:00Z"])


class SalaEsperaPrioridad(BaseModel):
    """Body para actualizar la prioridad de un paciente en sala de espera (Triage)."""

    prioridad: int = Field(..., ge=1, le=5, description="Nivel de prioridad/urgencia asignado (1-5)", examples=[3])
    motivo: Optional[str] = Field(None, description="Motivo de la consulta (opcional)", examples=["Control post-operatorio"])





class SalaEsperaAtender(BaseModel):
    """Body opcional para atender a un paciente vinculando un episodio médico existente o abriendo uno nuevo."""

    id_episodio: Optional[int] = Field(None, description="ID del episodio médico existente a vincular (opcional)", examples=[123])


class SalaEsperaLlamar(BaseModel):
    """Body para llamar a un paciente, asignando un consultorio físico."""

    consultorio: int = Field(..., ge=1, examples=[102])


class SalaEsperaUpdate(BaseModel):
    """Esquema interno para actualizar la entrada de sala de espera."""

    estado: Optional[EstadoSalaEspera] = None
    consultorio: Optional[int] = None


class SalaEsperaSchema(BaseModel):
    """Representación completa de un registro en la sala de espera."""

    id_espera: int
    id_paciente: int
    id_episodio: Optional[int] = None
    id_medico: int
    id_sede: int
    id_turno_m2: Optional[int] = None
    fecha_llegada: datetime
    fecha_turno: Optional[datetime] = None
    prioridad: int
    estado: EstadoSalaEspera
    consultorio: Optional[int] = None
    motivo: str

    model_config = {"from_attributes": True}
