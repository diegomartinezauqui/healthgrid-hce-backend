"""Schemas de órdenes médicas y alertas clínicas (Integración M4/M5 Estudios)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from common.enums.enums_orden import TipoAlertaClinica, TipoEstudio, PrioridadOrden

class AlertaClinicaSchema(BaseModel):
    """Alerta de seguridad clínica (Smart Payload para M4/M5)."""

    tipo: TipoAlertaClinica = Field(
        ..., examples=["CONTRAINDICACION_ABSOLUTA"]
    )
    descripcion: str = Field(
        ..., examples=["El paciente posee un marcapasos cardíaco."]
    )


class OrdenMedicaCompleta(BaseModel):
    """Orden médica con Smart Payload de alertas clínicas."""

    id_orden: int = Field(..., examples=[4050])
    id_paciente: int = Field(..., examples=[10500])
    tipo_estudio: TipoEstudio = Field(..., examples=["Imagen"])
    descripcion_pedido: Optional[str] = Field(
        None, examples=["Resonancia Magnética de Cerebro"]
    )
    prioridad: PrioridadOrden = Field(..., examples=["Urgente"])
    alertas_clinicas: List[AlertaClinicaSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrdenListResponse(BaseModel):
    """Respuesta de listado de órdenes."""

    status: str = Field(default="success", examples=["success"])
    cantidad: int = Field(..., examples=[1])
    data: List[OrdenMedicaCompleta]
