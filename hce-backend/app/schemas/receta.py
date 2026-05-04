"""Schemas de recetas y alertas farmacológicas (Integración M3 Farmacia)."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TipoAlertaFarmacologica(str, Enum):
    ALERGIA_MEDICAMENTOSA = "ALERGIA_MEDICAMENTOSA"
    INSUFICIENCIA_RENAL = "INSUFICIENCIA_RENAL"
    INSUFICIENCIA_HEPATICA = "INSUFICIENCIA_HEPATICA"
    EMBARAZO = "EMBARAZO"


class EstadoReceta(str, Enum):
    ACTIVA = "Activa"
    SUSPENDIDA = "Suspendida"
    DISPENSADA = "Dispensada"


class AlertaFarmacologicaSchema(BaseModel):
    """Alerta de seguridad farmacológica (Smart Payload para M3)."""

    tipo: TipoAlertaFarmacologica = Field(
        ..., examples=["ALERGIA_MEDICAMENTOSA"]
    )
    descripcion: str = Field(
        ..., examples=["Paciente reporta shock anafiláctico a la Penicilina en 2022."]
    )


class RecetaMedicaDetallada(BaseModel):
    """Receta electrónica con Smart Payload de alertas farmacológicas."""

    id_receta: int = Field(..., examples=[8502])
    id_paciente: int = Field(..., examples=[10500])
    id_evolucion: Optional[int] = Field(None, examples=[302])
    medicamento: str = Field(..., examples=["Amoxicilina 500mg"])
    indicaciones: Optional[str] = Field(
        None, examples=["Tomar 1 comprimido cada 8 horas por 7 días."]
    )
    estado: EstadoReceta = Field(..., examples=["Activa"])
    alertas_farmacologicas: List[AlertaFarmacologicaSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RecetaListResponse(BaseModel):
    """Respuesta paginada de recetas."""

    total: int = Field(..., examples=[15])
    data: List[RecetaMedicaDetallada]
