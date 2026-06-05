"""Capa de repositorios — acceso a datos (SQLAlchemy)."""

from app.repositories.base_repository import BaseRepository
from app.repositories.alerta_repository import alerta_repo
from app.repositories.antecedente_repository import antecedente_repo
from app.repositories.ficha_medica_repository import ficha_medica_repo
from app.repositories.paciente_repository import paciente_repo
from app.repositories.episodio_repository import episodio_repo
from app.repositories.acto_medico_repository import acto_medico_repo
from app.repositories.evolucion_repository import evolucion_repo
from app.repositories.receta_repository import receta_repo

__all__ = [
    "BaseRepository",
    "alerta_repo",
    "antecedente_repo",
    "ficha_medica_repo",
    "paciente_repo",
    "episodio_repo",
    "acto_medico_repo",
    "evolucion_repo",
    "receta_repo",
]
