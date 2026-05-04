"""Schemas de eventos Kafka publicados y consumidos por HCE."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# EVENTOS QUE HCE PUBLICA
# ═══════════════════════════════════════════════════════════════════


class EventoKafkaNuevaReceta(BaseModel):
    """
    Tópico: clinica.farmacia.receta_creada
    Suscriptores: M3 (Farmacia)
    """

    id_receta: int = Field(..., examples=[8502])
    tipo_paciente: str = Field(..., examples=["Internado"])  # Internado | Ambulatorio


class TipoEstudioKafka(str, Enum):
    LABORATORIO = "Laboratorio"
    IMAGEN = "Imagen"
    ANATOMIA_PATOLOGICA = "Anatomia_Patologica"


class EventoKafkaNuevaOrden(BaseModel):
    """
    Tópico: clinica.estudios.orden_creada
    Suscriptores: M4 (Laboratorio), M5 (Imágenes)
    """

    id_orden: int = Field(..., examples=[4050])
    tipo_estudio: TipoEstudioKafka = Field(..., examples=["Imagen"])


class TipoEpisodioKafka(str, Enum):
    CONSULTA_EXTERNA = "consulta-externa"
    INTERNACION = "internacion"
    GUARDIA = "guardia"
    CIRUGIA = "cirugia"


class EventoKafkaEpisodioCerrado(BaseModel):
    """
    Tópico: clinica.hce.episodio_cerrado
    Suscriptores: M7 (Facturación), M6 (Internación)
    """

    id_evento: UUID = Field(..., examples=["a3f2c1d4-89b0-4e5f-a123-456789abcdef"])
    tipo_evento: str = Field(default="episodio_cerrado", examples=["episodio_cerrado"])
    fecha_ocurrencia: datetime = Field(..., examples=["2025-03-15T11:00:00Z"])
    id_episodio: int = Field(..., examples=[700])
    id_paciente: int = Field(..., examples=[10500])
    id_sede: int = Field(..., examples=[3])
    tipo_episodio: TipoEpisodioKafka = Field(..., examples=["internacion"])
    id_medico_cierre: int = Field(..., examples=[42])
    total_actos_medicos: int = Field(..., examples=[4])
    id_obra_social: Optional[int] = Field(None, examples=[15])


class SeveridadPatologia(str, Enum):
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EventoKafkaPatologiaCritica(BaseModel):
    """
    Tópico: clinica.hce.patologia_critica_detectada
    Suscriptores: M10 (Core) — auditoría sanitaria
    """

    id_evento: UUID = Field(..., examples=["b7e3d2a1-45c6-4f78-b901-23456789cdef"])
    tipo_evento: str = Field(
        default="patologia_critica_detectada",
        examples=["patologia_critica_detectada"],
    )
    fecha_ocurrencia: datetime = Field(..., examples=["2025-04-01T14:00:00Z"])
    id_paciente: int = Field(..., examples=[10500])
    id_episodio: int = Field(..., examples=[700])
    codigo_patologia: str = Field(..., examples=["A15.0"])
    nombre_patologia: str = Field(..., examples=["Tuberculosis pulmonar"])
    id_medico_detecta: int = Field(..., examples=[42])
    id_sede: int = Field(..., examples=[3])
    severidad: SeveridadPatologia = Field(..., examples=["high"])


# ═══════════════════════════════════════════════════════════════════
# EVENTOS QUE HCE CONSUME
# ═══════════════════════════════════════════════════════════════════


class EventoKafkaPresentismo(BaseModel):
    """
    Tópico: clinica.turnos.presentismo (emitido por M2 Turnos)
    HCE lo consume para iniciar el flujo de atención.
    """

    id_turno_m2: int = Field(..., examples=[88402])
    id_paciente: int = Field(..., examples=[10500])
    id_profesional: str = Field(..., examples=["MP-12345"])
    fecha_hora_llegada: datetime = Field(..., examples=["2026-04-17T09:15:00Z"])
    motivo_turno: Optional[str] = Field(None, examples=["Control post-operatorio"])


# ═══════════════════════════════════════════════════════════════════
# NOTIFICACIÓN DE PERMISOS (HCE → M10)
# ═══════════════════════════════════════════════════════════════════


class TipoCambioPermiso(str, Enum):
    REVOKE_ACCESS = "revoke-access"
    ROLE_CHANGE = "role-change"
    DEACTIVATE_USER = "deactivate-user"


class PermissionChangeNotification(BaseModel):
    """Payload que HCE envía a Core para notificar cambio de permisos."""

    id_usuario_afectado: int = Field(..., examples=[42])
    tipo_cambio: TipoCambioPermiso = Field(..., examples=["revoke-access"])
    recurso_afectado: Optional[str] = Field(None, examples=["hce:write"])
    motivo: str = Field(
        ..., examples=["Profesional suspendido por auditoría interna."]
    )
    id_usuario_notificador: Optional[int] = Field(None, examples=[10])
    fecha_ocurrencia: Optional[datetime] = None


class PermissionChangeResponse(BaseModel):
    """Respuesta de Core tras recibir la notificación."""

    acknowledged: bool = Field(..., examples=[True])
