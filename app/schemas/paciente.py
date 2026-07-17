"""Schemas para Paciente (Caché de HCE)."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PacienteSchema(BaseModel):
    """Representación de un paciente almacenado en la caché de HCE."""

    id_paciente: int = Field(..., description="ID único del paciente (emitido por Core/M10)")
    datos_personales: Optional[Dict[str, Any]] = Field(None, description="Datos demográficos del paciente")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
