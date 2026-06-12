"""Schemas de recetas médicas (Integración M3 Farmacia)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaSmartPayload
from common.enums.enums_receta import EstadoReceta


class ItemRecetaCreate(BaseModel):
    """Payload para crear un ítem de receta."""

    medicamento: str = Field(..., max_length=300, examples=["Amoxicilina 500mg"])
    indicaciones: Optional[str] = Field(
        None, examples=["Tomar 1 comprimido cada 8 horas por 7 días."]
    )
    cantidad: int = Field(default=1, examples=[1])


class ItemRecetaSchema(BaseModel):
    """Esquema detallado de un ítem de receta."""

    id_item: int = Field(..., examples=[10])
    id_receta: int = Field(..., examples=[8502])
    medicamento: str = Field(..., max_length=300, examples=["Amoxicilina 500mg"])
    indicaciones: Optional[str] = Field(
        None, examples=["Tomar 1 comprimido cada 8 horas por 7 días."]
    )
    cantidad: int = Field(default=1, examples=[1])

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


class RecetaCreatedResponse(BaseModel):
    """Respuesta 201 tras crear una receta electrónica."""

    status: str = Field(default="success", examples=["success"])
    message: str = Field(
        default="Receta creada y evento Kafka publicado.",
        examples=["Receta creada y evento Kafka publicado."],
    )
    id_receta: int = Field(..., examples=[8502])


class RecetaListResponse(BaseModel):
    """Respuesta paginada de recetas."""

    total: int = Field(..., examples=[15])
    data: List[RecetaMedicaDetallada]
