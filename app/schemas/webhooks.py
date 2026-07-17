"""Schemas para Webhooks de Integración (Entrada)."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─── Módulo 2 (Turnos) Webhook Schemas ─────────────────────────────
class M2AppointmentInfo(BaseModel):
    id: int = Field(..., examples=[360])
    starts_at: datetime = Field(..., examples=["2026-09-29T12:00:00Z"])
    checked_in_at: datetime = Field(..., examples=["2026-06-24T17:22:34Z"])


class M2PatientInfo(BaseModel):
    id: int = Field(..., examples=[3365611])


class M2MedicInfo(BaseModel):
    id: int = Field(..., examples=[1361561151])


class M2CheckinWebhook(BaseModel):
    """Payload real del webhook de presentismo enviado por M2."""

    reason: str = Field(..., examples=["El paciente hizo checkin"])
    appointment: M2AppointmentInfo
    patient: M2PatientInfo
    medic: M2MedicInfo
    disclaimer: Optional[str] = Field(None, examples=["Notificación enviada por APPS 2 - Modulo 2"])


# ─── Módulo 5 (Imágenes) Webhook Schemas ───────────────────────────
class ReporteImagenWebhook(BaseModel):
    """Evento de reporte de imagen finalizado emitido por M5."""

    id_orden_hce: Optional[int] = Field(None, examples=[4051])
    report_id: Optional[str] = Field(None, examples=["RPT-9001"])
    id_paciente: int = Field(..., examples=[10500])
    titulo: Optional[str] = Field(None, examples=["Radiografía de Tórax"])
    informe: Optional[str] = Field(None, examples=["Sin hallazgos patológicos."])
    profesional_firmante: Optional[str] = Field(None, examples=["Dra. Gómez (Radiología)"])
    fecha_resultado: Optional[datetime] = None


# ─── Módulo 6 (Camas) Webhook Schemas ──────────────────────────────
class M6ResolucionWebhook(BaseModel):
    """Payload específico del webhook de resolución de cama enviado por M6."""

    solicitud_hce_id: str = Field(..., examples=["HCE-SOL-12"])
    decision: str = Field(..., examples=["APROBADA", "RECHAZADA"])
    cama: Optional[str] = Field(None, examples=["Cama 4"])
    habitacion: Optional[str] = Field(None, examples=["Hab 201"])
    motivo_rechazo: Optional[str] = Field(None, examples=["No hay camas disponibles."])
