from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from common.enums.enums_episodio import EstadoEpisodio, TipoActoMedico, TipoEpisodio


class ActoMedicoSchema(BaseModel):
    """Acto médico registrado dentro de un episodio."""

    id_acto_medico: int = Field(..., examples=[9001])
    id_episodio: int = Field(..., examples=[700])
    codigo_nomenclador: Optional[str] = Field(None, examples=["01.01.01"])
    descripcion: Optional[str] = Field(
        None, examples=["Consulta médica ambulatoria - primera vez"]
    )
    tipo: TipoActoMedico = Field(..., examples=["consulta"])
    id_profesional: Optional[int] = Field(None, examples=[42])
    fecha_realizacion: datetime = Field(..., examples=["2025-03-10T09:15:00Z"])
    cantidad: int = Field(default=1, examples=[1])
    observaciones: Optional[str] = None

    model_config = {"from_attributes": True}

# Schema para crear un episodio médico
class EpisodioCreate(BaseModel):
    """Creación de episodio médico."""

    tipo: TipoEpisodio = Field(..., examples=["internacion"])
    estado: EstadoEpisodio = Field(default=EstadoEpisodio.OPEN, examples=["open"])
    id_sede: Optional[int] = Field(None, examples=[3])
    diagnostico_principal: Optional[str] = Field(
        None, examples=["J18.9 - Neumonía no especificada"]
    )

    model_config = {"from_attributes": True}


class EpisodioUpdate(BaseModel):
    """Payload para actualizar un episodio médico (ej. cerrar o cambiar médico)."""

    tipo: Optional[TipoEpisodio] = None
    estado: Optional[EstadoEpisodio] = None
    id_sede: Optional[int] = None
    id_medico_responsable: Optional[int] = None
    diagnostico_principal: Optional[str] = Field(None, max_length=500)
    fecha_cierre: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActoMedicoCreate(BaseModel):
    """Payload para registrar un nuevo acto médico en un episodio."""

    codigo_nomenclador: Optional[str] = Field(None, max_length=20, examples=["01.01.01"])
    descripcion: Optional[str] = Field(None, max_length=500, examples=["Consulta médica ambulatoria"])
    tipo: TipoActoMedico = Field(..., examples=["consulta"])
    id_profesional: Optional[int] = Field(None, examples=[42])
    fecha_realizacion: Optional[datetime] = Field(None, description="Fecha de realización. Si no se envía, se usa la fecha/hora actual.")
    cantidad: int = Field(default=1, gt=0, examples=[1])
    observaciones: Optional[str] = None


class ActoMedicoUpdate(BaseModel):
    """Payload para actualizar parcialmente un acto médico."""

    codigo_nomenclador: Optional[str] = Field(None, max_length=20)
    descripcion: Optional[str] = Field(None, max_length=500)
    tipo: Optional[TipoActoMedico] = None
    id_profesional: Optional[int] = None
    fecha_realizacion: Optional[datetime] = None
    cantidad: Optional[int] = Field(None, gt=0)
    observaciones: Optional[str] = None

    model_config = {"from_attributes": True}


class EpisodioResumen(BaseModel):
    """Resumen de un episodio para listados."""

    id_episodio: int = Field(..., examples=[700])
    tipo: TipoEpisodio = Field(..., examples=["internacion"])
    estado: EstadoEpisodio = Field(..., examples=["closed"])
    id_sede: int = Field(..., examples=[3])
    fecha_apertura: datetime = Field(..., examples=["2025-03-10T09:00:00Z"])
    fecha_cierre: Optional[datetime] = Field(None, examples=["2025-03-15T11:00:00Z"])
    id_medico_responsable: int = Field(..., examples=[42])

    # NUEVOS CONTADORES AGREGADOS
    cant_evoluciones: int = Field(default=0, description="Cantidad de evoluciones clínicas en este episodio.")
    cant_recetas: int = Field(default=0, description="Cantidad de recetas digitales emitidas en este episodio.")
    cant_estudios: int = Field(default=0, description="Cantidad de pedidos de estudios médicos solicitados en este episodio.")

    model_config = {"from_attributes": True}


class EpisodioDetalle(BaseModel):
    """Detalle completo de un episodio con actos médicos."""

    id_episodio: int = Field(..., examples=[700])
    id_paciente: int = Field(..., examples=[10500])
    tipo: TipoEpisodio = Field(..., examples=["internacion"])
    estado: str = Field(..., examples=["CERRADO"])
    id_sede: int = Field(..., examples=[3])
    id_medico_responsable: int = Field(..., examples=[42])
    diagnostico_principal: Optional[str] = Field(
        None, examples=["J18.9 - Neumonía no especificada"]
    )
    fecha_apertura: datetime = Field(..., examples=["2025-03-10T09:00:00Z"])
    fecha_cierre: Optional[datetime] = Field(None, examples=["2025-03-15T11:00:00Z"])
    actos_medicos: List[ActoMedicoSchema] = Field(default_factory=list)

    # Campos de compatibilidad con M7 (Facturación)
    episodioId: Optional[int] = None
    pacienteId: Optional[int] = None
    tipoEpisodio: Optional[str] = None
    fechaInicio: Optional[datetime] = None
    fechaCierre: Optional[datetime] = None

    @model_validator(mode="after")
    def populate_m7_fields(self):
        self.episodioId = self.id_episodio
        self.pacienteId = self.id_paciente
        self.fechaInicio = self.fecha_apertura
        self.fechaCierre = self.fecha_cierre
        
        # Mapear tipo a tipoEpisodio
        tipo_val = self.tipo.value if hasattr(self.tipo, "value") else self.tipo
        if tipo_val == "internacion":
            self.tipoEpisodio = "INTERNACION"
        elif tipo_val == "guardia":
            self.tipoEpisodio = "GUARDIA"
        elif tipo_val == "consulta-externa":
            self.tipoEpisodio = "CONSULTA"
        elif tipo_val == "cirugia":
            self.tipoEpisodio = "CIRUGIA"
        else:
            self.tipoEpisodio = "OTRO"
            
        # Mapear estado a mayúsculas
        est_val = self.estado.value if hasattr(self.estado, "value") else self.estado
        if str(est_val).lower() in ("closed", "cerrado"):
            self.estado = "CERRADO"
        else:
            self.estado = "open"
            
        return self

    model_config = {"from_attributes": True}


class M7ActoMedicoResponse(BaseModel):
    """Acto médico con el formato plano esperado por M7."""

    idActoMedico: int = Field(..., examples=[88001])
    episodioId: int = Field(..., examples=[700])
    pacienteId: int = Field(..., examples=[10500])
    codigoPrestacion: Optional[str] = Field(None, examples=["80.01.02"])
    descripcion: Optional[str] = Field(None, examples=["Consulta médica especializada"])
    cantidad: int = Field(..., examples=[1])
    fechaRealizacion: datetime = Field(..., examples=["2026-07-15T14:30:00Z"])
    estado: str = Field(..., examples=["REALIZADO"])
    profesionalId: Optional[int] = Field(None, examples=[458])

    model_config = {"from_attributes": True}


class EpisodioListResponse(BaseModel):
    """Lista de episodios de un paciente."""

    id_paciente: int = Field(..., examples=[10500])
    total: int = Field(..., examples=[5])
    episodios: List[EpisodioResumen]


class ActoMedicoListResponse(BaseModel):
    """Lista de actos médicos de un episodio."""

    id_episodio: int = Field(..., examples=[700])
    total: int = Field(..., examples=[4])
    actos_medicos: List[ActoMedicoSchema]
