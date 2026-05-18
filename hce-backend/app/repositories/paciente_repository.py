"""Repositorio de Paciente — extiende BaseRepository."""

from app.models.paciente import Paciente
from app.repositories.base_repository import BaseRepository


class PacienteRepository(BaseRepository[Paciente, None]):  # type: ignore[type-var]
    """
    Repositorio de Paciente.

    Hereda de BaseRepository:
      - get(db, pk)      → buscar por id_paciente
      - exists(db, pk)   → verificar si existe un paciente
      - get_all(db)      → listar todos
      - save / update / delete → operaciones de escritura

    Este módulo HCE no crea ni modifica pacientes (eso lo hace M10 - Core).
    Solo necesitamos lectura/existencia para validaciones.
    """

    def __init__(self) -> None:
        super().__init__(Paciente, Paciente.id_paciente)


# Singleton listo para inyectar en los services
paciente_repo = PacienteRepository()
