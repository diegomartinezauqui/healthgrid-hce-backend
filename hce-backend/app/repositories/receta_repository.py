"""Repositorio para la gestión de Recetas y sus Ítems."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item_receta import ItemReceta
from app.models.receta import Receta
from app.repositories.base_repository import BaseRepository
from app.schemas.receta import ItemRecetaCreate, RecetaCreate


class RecetaRepository(BaseRepository[Receta, RecetaCreate]):
    def __init__(self):
        super().__init__(Receta, Receta.id_receta)

    async def get_receta_detallada(
        self, db: AsyncSession, id_receta: int
    ) -> Optional[Receta]:
        """Obtiene una receta por su ID incluyendo sus ítems."""
        result = await db.execute(
            select(Receta)
            .options(selectinload(Receta.items))
            .where(Receta.id_receta == id_receta)
        )
        return result.scalars().first()

    async def get_recetas_filtradas(
        self,
        db: AsyncSession,
        estado: Optional[str] = None,
        id_paciente: Optional[int] = None,
        desde_fecha: Optional[str] = None,
    ) -> list[Receta]:
        """Obtiene recetas aplicando filtros y cargando sus ítems."""
        query = select(Receta).options(selectinload(Receta.items))

        if estado:
            query = query.where(Receta.estado == estado)
        if id_paciente:
            query = query.where(Receta.id_paciente == id_paciente)
        # Nota: La tabla recetas actual no tiene fecha. Si tuviera, filtraríamos por desde_fecha aquí.

        result = await db.execute(query)
        return list(result.scalars().all())

    async def actualizar_estado(
        self, db: AsyncSession, receta: Receta, estado: str
    ) -> Receta:
        """Actualiza el estado de una receta."""
        receta.estado = estado
        db.add(receta)
        await db.flush()
        return receta


receta_repo = RecetaRepository()
