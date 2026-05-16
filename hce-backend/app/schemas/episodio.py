"""Schemas de episodios y actos médicos (Integración M7 Facturación)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

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

    id_paciente: int = Field(..., examples=[10500])
    tipo: TipoEpisodio = Field(..., examples=["internacion"])
    estado: EstadoEpisodio = Field(..., examples=["closed"])
    id_sede: int = Field(..., examples=[3])
    id_medico_responsable: int = Field(..., examples=[42])
    diagnostico_principal: Optional[str] = Field(
        None, examples=["J18.9 - Neumonía no especificada"]
    )

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

    model_config = {"from_attributes": True}


class EpisodioDetalle(BaseModel):
    """Detalle completo de un episodio con actos médicos."""

    id_episodio: int = Field(..., examples=[700])
    id_paciente: int = Field(..., examples=[10500])
    tipo: TipoEpisodio = Field(..., examples=["internacion"])
    estado: EstadoEpisodio = Field(..., examples=["closed"])
    id_sede: int = Field(..., examples=[3])
    id_medico_responsable: int = Field(..., examples=[42])
    diagnostico_principal: Optional[str] = Field(
        None, examples=["J18.9 - Neumonía no especificada"]
    )
    fecha_apertura: datetime = Field(..., examples=["2025-03-10T09:00:00Z"])
    fecha_cierre: Optional[datetime] = Field(None, examples=["2025-03-15T11:00:00Z"])
    actos_medicos: List[ActoMedicoSchema] = Field(default_factory=list)

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
