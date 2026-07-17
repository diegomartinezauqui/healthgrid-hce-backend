from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.alerta import AlertaCreate, AlertaSchema
from app.schemas.antecedente import AntecedenteCreate, AntecedenteSchema


class FichaMedicaBase(BaseModel):
    """Atributos compartidos entre Create y Update."""

    grupo_sanguineo: Optional[str] = Field(
        None,
        max_length=10,
        examples=["A+"],
        description="Grupo sanguíneo y factor Rh del paciente.",
    )
    peso_kg: Optional[float] = Field(
        None,
        examples=[72.5],
        description="Peso del paciente en kilogramos.",
    )
    altura_cm: Optional[float] = Field(
        None,
        examples=[175.0],
        description="Altura del paciente en centímetros.",
    )
    observaciones_generales: Optional[str] = Field(
        None,
        examples=["Paciente con antecedentes de hipertensión arterial. Diabético tipo 2."],
        description="Notas generales y antecedentes del paciente visibles en la cabecera de la ficha.",
    )


class FichaMedicaCreate(FichaMedicaBase):
    """Payload para crear/registrar la ficha médica de un paciente."""

    # El id_paciente viene de la URL del endpoint, no del body
    pass


class FichaMedicaUpdate(FichaMedicaBase):
    """Payload para actualizar parcialmente la ficha médica. Todos los campos son opcionales."""

    pass


class FichaMedicaSchema(FichaMedicaBase):
    """Schema de respuesta completo de la ficha médica."""

    id_paciente: int = Field(..., examples=[10500])

    model_config = {"from_attributes": True}


class FichaMedicaCompletaCreate(BaseModel):
    """Payload para registrar de forma atómica la ficha médica, antecedentes y alertas de un paciente."""

    ficha_medica: FichaMedicaCreate
    antecedentes: List[AntecedenteCreate] = Field(default_factory=list)
    alertas_clinicas: List[AlertaCreate] = Field(default_factory=list)

    # Campos demográficos opcionales del Paciente
    dni: Optional[str] = Field(None, description="DNI del paciente")
    fecha_nacimiento: Optional[str] = Field(None, description="Fecha de nacimiento (YYYY-MM-DD)")
    genero: Optional[str] = Field(None, description="Género/Sexo del paciente")
    nombre_obra_social: Optional[str] = Field(None, description="Nombre de la Obra Social (ej: 'OSDE')")
    nombre_plan: Optional[str] = Field(None, description="Nombre del Plan (ej: 'OSDE 310')")
    entidadFinanciadoraId: Optional[int] = Field(None, description="ID de la Entidad Financiadora en M7")
    planId: Optional[int] = Field(None, description="ID del Plan en M7")
    numero_afiliado: Optional[str] = Field(None, description="Número de afiliado del paciente")
    telefono: Optional[str] = Field(None, description="Teléfono del paciente")
    direccion: Optional[str] = Field(None, description="Dirección del paciente")


class FichaMedicaCompletaResponse(BaseModel):
    """Schema de respuesta completo para la ficha médica consolidada con sus antecedentes y alertas."""

    ficha_medica: FichaMedicaSchema
    antecedentes: List[AntecedenteSchema] = Field(default_factory=list)
    alertas_clinicas: List[AlertaSchema] = Field(default_factory=list)
