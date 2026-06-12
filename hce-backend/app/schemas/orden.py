"""Schemas de órdenes médicas (Integración M4/M5 Estudios)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaSmartPayload
from common.enums.enums_orden import TipoEstudio, PrioridadOrden


class OrdenCreate(BaseModel):
    """Payload para crear una nueva orden médica de estudio."""

    tipo_estudio: TipoEstudio = Field(..., examples=["Imagen"])
    descripcion_pedido: Optional[str] = Field(
        None,
        max_length=500,
        examples=["Resonancia Magnética de Cerebro con contraste"],
    )
    prioridad: PrioridadOrden = Field(
        default=PrioridadOrden.NORMAL,
        examples=["Normal"],
    )


class OrdenMedicaCompleta(BaseModel):
    """Orden médica con Smart Payload de alertas clínicas activas."""

    id_orden: int = Field(..., examples=[4050])
    id_paciente: int = Field(..., examples=[10500])
    tipo_estudio: TipoEstudio = Field(..., examples=["Imagen"])
    descripcion_pedido: Optional[str] = Field(
        None, examples=["Resonancia Magnética de Cerebro"]
    )
    prioridad: PrioridadOrden = Field(..., examples=["Urgente"])
    alertas_clinicas: List[AlertaSmartPayload] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrdenCreatedResponse(BaseModel):
    """Respuesta 201 tras crear una orden médica."""

    status: str = Field(default="success", examples=["success"])
    message: str = Field(
        default="Orden creada y evento Kafka publicado.",
        examples=["Orden creada y evento Kafka publicado."],
    )
    id_orden: int = Field(..., examples=[4050])


class OrdenListResponse(BaseModel):
    """Respuesta de listado de órdenes."""

    status: str = Field(default="success", examples=["success"])
    cantidad: int = Field(..., examples=[1])
    data: List[OrdenMedicaCompleta]
