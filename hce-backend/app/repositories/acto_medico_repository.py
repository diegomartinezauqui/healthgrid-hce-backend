"""Repositorio de ActoMedico."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acto_medico import ActoMedico
from app.repositories.base_repository import BaseRepository
from app.schemas.episodio import ActoMedicoUpdate


class ActoMedicoRepository(BaseRepository[ActoMedico, ActoMedicoUpdate]):
    """
    Repositorio de ActoMedico.
    Hereda CRUD básico de BaseRepository.
    """

    def __init__(self) -> None:
        super().__init__(ActoMedico, ActoMedico.id_acto_medico)

    async def get_by_episodio(
        self, db: AsyncSession, id_episodio: int
    ) -> Sequence[ActoMedico]:
        """Obtener todos los actos médicos de un episodio específico."""
        result = await db.execute(
            select(self.model).where(self.model.id_episodio == id_episodio)
        )
        return result.scalars().all()


# Singleton
acto_medico_repo = ActoMedicoRepository()
