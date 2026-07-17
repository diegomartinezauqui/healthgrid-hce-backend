"""Schemas de resultados de estudios (Integración M4/M5 → HCE)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from common.enums.enums_orden import TipoEstudio, SubtipoEstudio


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
    subtipo: Optional[SubtipoEstudio] = Field(
        None, examples=["ECOGRAFY"]
    )
    link_imagen: Optional[str] = Field(
        None, examples=["https://viewer.pacs.hospital/study/1234"]
    )
    url_detalle: Optional[str] = Field(
        None, examples=["https://api.imagenes.hospital/v1/estudios/1234/completo"]
    )


# ─── Schemas para Webhook de Laboratorio (Módulo 4) ────────────────
class LabOrdenInfo(BaseModel):
    id_laboratorio: int
    id_orden_hce: Optional[int] = None
    descripcion: Optional[str] = None
    prioridad: Optional[str] = None
    fecha_solicitud: Optional[datetime] = None
    fecha_resultado: Optional[datetime] = None


class LabPacienteInfo(BaseModel):
    id: int
    nombre: Optional[str] = None
    dni: Optional[str] = None


class LabResumenInfo(BaseModel):
    total_analitos: int
    analitos_fuera_de_rango: int
    hay_valores_criticos: bool


class LabRangoNormal(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class LabAnalitoInfo(BaseModel):
    nombre: str
    valor: float
    unidad: Optional[str] = None
    rango_normal: Optional[LabRangoNormal] = None
    fuera_de_rango: bool
    es_critico: bool
    observacion: Optional[str] = None


class ResultadoLaboratorioWebhook(BaseModel):
    """Payload específico del webhook laboratorio.resultado_listo (M4)."""

    evento: str = Field(..., examples=["laboratorio.resultado_listo"])
    version: str = Field(..., examples=["1.0"])
    id_evento: str = Field(..., examples=["uuid"])
    fecha_ocurrencia: datetime
    orden: LabOrdenInfo
    paciente: LabPacienteInfo
    profesional_firmante: str
    resumen: LabResumenInfo
    analitos: List[LabAnalitoInfo]


class ResultadoEstudioResumen(BaseModel):
    """Resumen de resultado para el Portal del Paciente (M8) y consumo interno HCE."""

    id_resultado: int = Field(..., examples=[9021])
    id_orden: Optional[int] = Field(None, examples=[4050])
    tipo_estudio: str = Field(..., examples=["Laboratorio"])
    fecha_resultado: datetime = Field(..., examples=["2026-04-20T10:00:00Z"])
    titulo: Optional[str] = Field(None, examples=["Hemograma Completo"])
    resumen: Optional[str] = Field(
        None, examples=["Valores dentro de los rangos normales. Sin observaciones."]
    )
    profesional_firmante: Optional[str] = Field(
        None, examples=["Dr. Bioq. Fernandez"]
    )
    subtipo: Optional[SubtipoEstudio] = None
    link_imagen: Optional[str] = None
    url_detalle: Optional[str] = None
    analitos: Optional[List[dict]] = None
    resumen_analitos: Optional[dict] = None

    # Compatibilidad con M5 / Front
    id_externo_estudio: Optional[str] = None
    report_id: Optional[str] = None

    @model_validator(mode="after")
    def populate_aliases(self):
        if self.id_externo_estudio and not self.report_id:
            self.report_id = self.id_externo_estudio
        elif self.report_id and not self.id_externo_estudio:
            self.id_externo_estudio = self.report_id
        return self

    model_config = {"from_attributes": True}


class ResultadoCreatedResponse(BaseModel):
    """Respuesta tras registrar un resultado."""

    status: str = Field(default="success", examples=["success"])
    message: str = Field(
        default="Resultado vinculado correctamente a la Historia Clínica.",
        examples=["Resultado vinculado correctamente a la Historia Clínica."],
    )


class ResultadoLaboratorioSchema(BaseModel):
    id_resultado_laboratorio: int
    id_orden: Optional[int] = None
    id_paciente: int
    id_profesional_firmante: str
    fecha_resultado: datetime
    informe_resumen: Optional[str] = None
    id_externo_estudio: Optional[str] = None
    analitos: Optional[List[dict]] = None
    resumen_analitos: Optional[dict] = None

    model_config = {"from_attributes": True}


class ResultadoImagenSchema(BaseModel):
    id_resultado_imagen: int
    id_orden: Optional[int] = None
    id_paciente: int
    id_profesional_firmante: str
    fecha_resultado: datetime
    titulo: Optional[str] = None
    informe_resumen: Optional[str] = None
    id_externo_estudio: Optional[str] = None
    subtipo: Optional[SubtipoEstudio] = None
    link_imagen: Optional[str] = None
    url_detalle: Optional[str] = None

    model_config = {"from_attributes": True}
