"""Enums de antecedentes del paciente."""

from enum import Enum


class TipoAntecedente(str, Enum):
    """Tipo de antecedente clínico del paciente."""
    QUIRURGICO = "Quirurgico"
    FAMILIAR = "Familiar"
    PATOLOGICO = "Patologico"
    HABITO = "Habito"
