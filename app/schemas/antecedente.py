"""Schemas de antecedentes clínicos del paciente."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from common.enums.enums_antecedente import TipoAntecedente


class AntecedenteCreate(BaseModel):
    """Body para registrar un nuevo antecedente."""

    tipo: TipoAntecedente = Field(..., examples=["Quirurgico"])
    descripcion: str = Field(..., examples=["Colecistectomía laparoscópica"])
    fecha_suceso: Optional[date] = Field(None, examples=["2018-04-15"])
    observaciones: Optional[str] = Field(None, examples=["Sin complicaciones postoperatorias."])


class AntecedenteUpdate(BaseModel):
    """Body para actualización parcial de un antecedente (PATCH)."""

    descripcion: Optional[str] = None
    fecha_suceso: Optional[date] = None
    observaciones: Optional[str] = None


class AntecedenteSchema(BaseModel):
    """Respuesta completa de un antecedente clínico."""

    id: int
    id_paciente: int
    tipo: TipoAntecedente
    descripcion: str
    fecha_suceso: Optional[date] = None
    observaciones: Optional[str] = None
    fecha_registro: datetime
    id_medico_registro: int

    model_config = {"from_attributes": True}
