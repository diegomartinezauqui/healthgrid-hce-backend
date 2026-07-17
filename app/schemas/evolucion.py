"""Schemas de evoluciones médicas (notas de consulta)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EvolucionCreate(BaseModel):
    """Body para registrar una nueva evolución médica en un episodio."""

    contenido: str = Field(
        ...,
        examples=["Paciente refiere mejoría del cuadro respiratorio. Se auscultan campos pulmonares limpios. Se indica continuar tratamiento."],
        description="Texto libre con la nota clínica del profesional.",
    )
    # id_profesional se obtiene del JWT (user.sub), no del body.
    # fecha se genera automáticamente si no se envía.
    fecha: Optional[datetime] = Field(
        None,
        description="Fecha/hora de la evolución. Si no se envía, se usa la fecha/hora actual.",
    )


class EvolucionUpdate(BaseModel):
    """Body para actualizar parcialmente una evolución médica (PATCH)."""

    contenido: Optional[str] = Field(
        None,
        description="Texto libre con la nota clínica corregida.",
    )

    model_config = {"from_attributes": True}


class EvolucionSchema(BaseModel):
    """Schema de respuesta completo de una evolución médica."""

    id_evolucion: int
    id_episodio: int
    id_profesional: int
    contenido: Optional[str] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class EvolucionListResponse(BaseModel):
    """Respuesta de listado de evoluciones de un episodio."""

    id_episodio: int
    total: int
    evoluciones: List[EvolucionSchema]
