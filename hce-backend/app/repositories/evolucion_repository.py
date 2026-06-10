"""Repositorio de Evolucion."""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolucion import Evolucion
from app.repositories.base_repository import BaseRepository
from app.schemas.evolucion import EvolucionUpdate


class EvolucionRepository(BaseRepository[Evolucion, EvolucionUpdate]):
    """
    Repositorio de Evolucion.
    Hereda CRUD básico de BaseRepository.
    """

    def __init__(self) -> None:
        super().__init__(Evolucion, Evolucion.id_evolucion)

    async def get_by_episodio(
        self, db: AsyncSession, id_episodio: int
    ) -> Sequence[Evolucion]:
        """Obtener todas las evoluciones de un episodio, ordenadas por fecha."""
        result = await db.execute(
            select(self.model)
            .where(self.model.id_episodio == id_episodio)
            .order_by(self.model.fecha.asc())
        )
        return result.scalars().all()

    async def get_by_episodio_and_id(
        self, db: AsyncSession, id_episodio: int, id_evolucion: int
    ) -> Optional[Evolucion]:
        """Obtener una evolución específica verificando que pertenezca al episodio."""
        result = await db.execute(
            select(self.model).where(
                self.model.id_evolucion == id_evolucion,
                self.model.id_episodio == id_episodio,
            )
        )
        return result.scalar_one_or_none()


# Singleton
evolucion_repo = EvolucionRepository()
