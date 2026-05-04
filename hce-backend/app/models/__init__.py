"""
Modelos SQLAlchemy del módulo HCE.
Importar todos los modelos aquí para que Alembic los detecte.
"""

from app.models.acto_medico import ActoMedico
from app.models.alerta_clinica import AlertaClinica
from app.models.alerta_farmacologica import AlertaFarmacologica
from app.models.cobertura_medica import CoberturaMedica
from app.models.episodio import Episodio
from app.models.evolucion import Evolucion
from app.models.movimiento_internacion import MovimientoInternacion
from app.models.orden import Orden
from app.models.paciente import Paciente
from app.models.receta import Receta
from app.models.resultado import Resultado

__all__ = [
    "Paciente",
    "Episodio",
    "Evolucion",
    "ActoMedico",
    "Receta",
    "Orden",
    "Resultado",
    "AlertaClinica",
    "AlertaFarmacologica",
    "CoberturaMedica",
    "MovimientoInternacion",
]
