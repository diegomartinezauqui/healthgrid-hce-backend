"""Repositorio de AntecedentePaciente."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.antecedente_paciente import AntecedentePaciente
from app.repositories.base_repository import BaseRepository
from app.schemas.antecedente import AntecedenteCreate, AntecedenteUpdate


class AntecedenteRepository(BaseRepository[AntecedentePaciente, AntecedenteUpdate]):
    """
    Repositorio de AntecedentePaciente.

    Hereda de BaseRepository:
      - get(db, pk)           → buscar por id
      - exists(db, pk)        → verificar existencia
      - save(db, instance)    → INSERT
      - update(db, obj, data) → PATCH parcial
      - delete(db, pk)        → DELETE

    Métodos específicos:
      - get_by_paciente       → todos los antecedentes de un paciente
      - create                → construye la entidad y llama a save()
    """

    def __init__(self) -> None:
        super().__init__(AntecedentePaciente, AntecedentePaciente.id)

    async def get_by_paciente(
        self, db: AsyncSession, id_paciente: int
    ) -> list[AntecedentePaciente]:
        """Todos los antecedentes de un paciente."""
        result = await db.execute(
            select(AntecedentePaciente).where(
                AntecedentePaciente.id_paciente == id_paciente
            )
        )
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, id_paciente: int, data: AntecedenteCreate, id_medico: int
    ) -> AntecedentePaciente:
        """Construye la entidad con los datos del schema y la persiste."""
        antecedente = AntecedentePaciente(
            id_paciente=id_paciente,
            tipo=data.tipo,
            descripcion=data.descripcion,
            fecha_suceso=data.fecha_suceso,
            observaciones=data.observaciones,
            id_medico_registro=id_medico,
        )
        return await self.save(db, antecedente)


# Singleton
antecedente_repo = AntecedenteRepository()
