"""Schemas de recetas médicas (Integración M3 Farmacia)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaSmartPayload
from common.enums.enums_receta import EstadoReceta


class ItemRecetaBase(BaseModel):
    medicamento: str = Field(..., examples=["Amoxicilina 500mg"], max_length=300)
    indicaciones: Optional[str] = Field(
        None, examples=["Tomar 1 comprimido cada 8 horas por 7 días."]
    )
    cantidad: int = Field(1, examples=[1], ge=1)


class ItemRecetaCreate(ItemRecetaBase):
    """Schema para crear un ítem de receta."""
    pass


class ItemRecetaSchema(ItemRecetaBase):
    """Schema para leer un ítem de receta."""
    id_item: int = Field(..., examples=[1])
    id_receta: int = Field(..., examples=[8502])

    model_config = {"from_attributes": True}


class RecetaCreate(BaseModel):
    """Payload para que un médico cree una receta completa con múltiples medicamentos."""
    items: List[ItemRecetaCreate] = Field(..., min_length=1)


class RecetaMedicaDetallada(BaseModel):
    """Receta electrónica con Smart Payload de alertas clínicas activas del paciente."""

    id_receta: int = Field(..., examples=[8502])
    id_paciente: int = Field(..., examples=[10500])
    id_evolucion: Optional[int] = Field(None, examples=[302])
    estado: EstadoReceta = Field(..., examples=["Activa"])
    items: List[ItemRecetaSchema] = Field(default_factory=list)
    alertas_clinicas: List[AlertaSmartPayload] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RecetaListResponse(BaseModel):
    """Respuesta paginada de recetas."""

    total: int = Field(..., examples=[15])
    data: List[RecetaMedicaDetallada]
