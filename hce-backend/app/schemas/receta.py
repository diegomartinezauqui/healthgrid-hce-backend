"""Schemas de recetas médicas (Integración M3 Farmacia)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaSmartPayload
from common.enums.enums_receta import EstadoReceta


class RecetaMedicaDetallada(BaseModel):
    """Receta electrónica con Smart Payload de alertas clínicas activas del paciente."""

    id_receta: int = Field(..., examples=[8502])
    id_paciente: int = Field(..., examples=[10500])
    id_evolucion: Optional[int] = Field(None, examples=[302])
    medicamento: str = Field(..., examples=["Amoxicilina 500mg"])
    indicaciones: Optional[str] = Field(
        None, examples=["Tomar 1 comprimido cada 8 horas por 7 días."]
    )
    estado: EstadoReceta = Field(..., examples=["Activa"])
    alertas_clinicas: List[AlertaSmartPayload] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RecetaListResponse(BaseModel):
    """Respuesta paginada de recetas."""

    total: int = Field(..., examples=[15])
    data: List[RecetaMedicaDetallada]
