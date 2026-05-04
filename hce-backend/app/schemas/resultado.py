"""Schemas de resultados de estudios (Integración M4/M5 → HCE)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.orden import TipoEstudio


class ResultadoEstudioRequest(BaseModel):
    """Payload enviado por M4/M5 para registrar un resultado en la HCE."""

    id_orden: Optional[int] = Field(None, examples=[4050])
    id_paciente: int = Field(..., examples=[10500])
    tipo_estudio: TipoEstudio = Field(..., examples=["Imagen"])
    id_profesional_firmante: str = Field(
        ..., examples=["Dra. Gomez (Radiología)"]
    )
    fecha_resultado: datetime = Field(
        ..., examples=["2026-04-17T11:00:00Z"]
    )
    informe_resumen: Optional[str] = Field(
        None, examples=["RM de Cerebro: Sin hallazgos patológicos."]
    )
    id_externo_estudio: Optional[str] = Field(
        None, examples=["550e8400-e29b-41d4-a716-446655440000"]
    )


class ResultadoEstudioResumen(BaseModel):
    """Resumen de resultado para el Portal del Paciente (M8)."""

    id_resultado: int = Field(..., examples=[9021])
    tipo_estudio: str = Field(..., examples=["Laboratorio"])
    fecha_resultado: datetime = Field(..., examples=["2026-04-20T10:00:00Z"])
    titulo: Optional[str] = Field(None, examples=["Hemograma Completo"])
    resumen: Optional[str] = Field(
        None, examples=["Valores dentro de los rangos normales. Sin observaciones."]
    )
    profesional_firmante: Optional[str] = Field(
        None, examples=["Dr. Bioq. Fernandez"]
    )

    model_config = {"from_attributes": True}


class ResultadoCreatedResponse(BaseModel):
    """Respuesta tras registrar un resultado."""

    status: str = Field(default="success", examples=["success"])
    message: str = Field(
        default="Resultado vinculado correctamente a la Historia Clínica.",
        examples=["Resultado vinculado correctamente a la Historia Clínica."],
    )
