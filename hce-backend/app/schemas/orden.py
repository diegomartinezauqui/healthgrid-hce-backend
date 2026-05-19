"""Schemas de órdenes médicas (Integración M4/M5 Estudios)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaSmartPayload
from common.enums.enums_orden import TipoEstudio, PrioridadOrden


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


class OrdenListResponse(BaseModel):
    """Respuesta de listado de órdenes."""

    status: str = Field(default="success", examples=["success"])
    cantidad: int = Field(..., examples=[1])
    data: List[OrdenMedicaCompleta]
