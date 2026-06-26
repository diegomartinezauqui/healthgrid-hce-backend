"""Schemas de órdenes médicas (Integración M4/M5 Estudios)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaSmartPayload
from common.enums.enums_orden import TipoEstudio, PrioridadOrden, SubtipoEstudio


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
    id_episodio: Optional[int] = Field(None, examples=[101])
    id_evolucion: Optional[int] = Field(None, examples=[202])


class OrdenLaboratorioCreate(BaseModel):
    """Payload para crear una nueva orden de laboratorio."""

    estudio_ids: List[int] = Field(..., description="Lista de IDs de estudios del catálogo M4", examples=[[1, 2]])
    descripcion_pedido: Optional[str] = Field(None, max_length=500, examples=["Indicaciones adicionales para la extracción"])
    prioridad: PrioridadOrden = Field(default=PrioridadOrden.NORMAL, examples=["Normal"])
    id_episodio: Optional[int] = Field(None, examples=[101])
    id_evolucion: Optional[int] = Field(None, examples=[202])


class OrdenImagenCreate(BaseModel):
    """Payload para crear una nueva orden de imágenes."""

    subtipo: SubtipoEstudio = Field(..., description="Tipo/modalidad del estudio de imagen", examples=["RESONANCE"])
    descripcion_pedido: Optional[str] = Field(None, max_length=500, examples=["Resonancia de cerebro con contraste"])
    prioridad: PrioridadOrden = Field(default=PrioridadOrden.NORMAL, examples=["Normal"])
    id_episodio: Optional[int] = Field(None, examples=[101])
    id_evolucion: Optional[int] = Field(None, examples=[202])


class OrdenMedicaCompleta(BaseModel):
    """Orden médica con Smart Payload de alertas clínicas activas."""

    id_orden: int = Field(..., examples=[4050])
    id_paciente: int = Field(..., examples=[10500])
    tipo_estudio: TipoEstudio = Field(..., examples=["Imagen"])
    descripcion_pedido: Optional[str] = Field(
        None, examples=["Resonancia Magnética de Cerebro"]
    )
    prioridad: PrioridadOrden = Field(..., examples=["Urgente"])
    id_episodio: Optional[int] = Field(None, examples=[101])
    id_evolucion: Optional[int] = Field(None, examples=[202])
    fecha_creacion: datetime = Field(..., examples=["2026-06-25T14:30:00Z"])
    id_medico_solicitante: Optional[int] = Field(None, examples=[42])
    subtipo: Optional[SubtipoEstudio] = Field(None, examples=["RESONANCE"])
    estudio_ids: Optional[List[int]] = Field(None, examples=[[1, 2]])
    estado: str = Field(default="Pendiente", examples=["Pendiente"])
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
