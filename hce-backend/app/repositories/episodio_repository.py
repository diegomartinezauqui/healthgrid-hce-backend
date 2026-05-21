"""Repositorio de Episodio."""

from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.episodio import Episodio
from app.repositories.base_repository import BaseRepository
from app.schemas.episodio import EpisodioUpdate


class EpisodioRepository(BaseRepository[Episodio, EpisodioUpdate]):
    """
    Repositorio de Episodio.
    Hereda CRUD básico de BaseRepository.
    """

    def __init__(self) -> None:
        super().__init__(Episodio, Episodio.id_episodio)

    async def get_by_paciente(
        self,
        db: AsyncSession,
        id_paciente: int,
        estado: Optional[str] = None,
        desde_fecha: Optional[date] = None,
        hasta_fecha: Optional[date] = None,
    ) -> Sequence[Episodio]:
        """Obtener episodios de un paciente con filtros opcionales."""
        query = select(self.model).where(self.model.id_paciente == id_paciente)

        if estado and estado != "all":
            query = query.where(self.model.estado == estado)
        if desde_fecha:
            query = query.where(self.model.fecha_apertura >= desde_fecha)
        if hasta_fecha:
            query = query.where(self.model.fecha_apertura <= hasta_fecha)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_detalle(
        self, db: AsyncSession, id_paciente: int, id_episodio: int
    ) -> Optional[Episodio]:
        """Obtener detalle de un episodio con actos médicos cargados (selectinload)."""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.actos_medicos))
            .where(
                self.model.id_episodio == id_episodio,
                self.model.id_paciente == id_paciente,
            )
        )
        return result.scalar_one_or_none()


# Singleton
episodio_repo = EpisodioRepository()
