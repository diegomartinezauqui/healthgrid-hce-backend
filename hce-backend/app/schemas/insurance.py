"""Schemas de cobertura médica / obra social (Integración M7 Facturación)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class InsuranceResponse(BaseModel):
    """Cobertura médica vigente del paciente."""

    id_paciente: int = Field(..., examples=[10500])
    id_obra_social: int = Field(..., examples=[15])
    nombre_obra_social: str = Field(..., examples=["OSDE"])
    codigo_plan: Optional[str] = Field(None, examples=["OSDE-210"])
    numero_afiliado: Optional[str] = Field(None, examples=["1234567890"])
    vigente_desde: Optional[date] = Field(None, examples=["2024-01-01"])
    vigente_hasta: Optional[date] = Field(None)

    model_config = {"from_attributes": True}
