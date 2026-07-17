"""Schemas de cobertura médica / obra social (Integración M7 Facturación)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class InsuranceResponse(BaseModel):
    """Cobertura médica vigente del paciente."""

    id_paciente: int = Field(..., examples=[10500])
    entidadFinanciadoraId: int = Field(..., examples=[1])
    nombre_obra_social: str = Field(..., examples=["OSDE"])
    nombre_plan: Optional[str] = Field(None, examples=["OSDE 310"])
    planId: Optional[str] = Field(None, examples=["2"])
    numero_afiliado: Optional[str] = Field(None, examples=["1234567890"])

    # Compatibilidad con M7 (Facturación)
    id_obra_social: Optional[int] = Field(None, description="Alias de entidadFinanciadoraId para M7")
    codigo_plan: Optional[int] = Field(None, description="Alias de planId para M7")

    model_config = {"from_attributes": True}

