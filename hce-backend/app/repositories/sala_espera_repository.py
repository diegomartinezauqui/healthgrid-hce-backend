"""Repositorio para la gestión de la Sala de Espera."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sala_espera import SalaEspera
from app.repositories.base_repository import BaseRepository
from app.schemas.sala_espera import SalaEsperaUpdate


class SalaEsperaRepository(BaseRepository[SalaEspera, SalaEsperaUpdate]):
    def __init__(self) -> None:
        super().__init__(SalaEspera, SalaEspera.id_espera)

    async def get_sala_filtrada(
        self,
        db: AsyncSession,
        id_medico: Optional[int] = None,
        id_sede: Optional[int] = None,
        estado: Optional[str] = None,
        ordenar_por: Optional[str] = None,
    ) -> List[SalaEspera]:
        """
        Obtiene los registros de la sala de espera aplicando filtros y ordenamiento flexible.
        
        Parámetros:
        - ordenar_por: 'llegada' (fecha_llegada asc), 'turno' (fecha_turno asc nulls last), 'prioridad' (prioridad desc).
        """
        query = select(SalaEspera)

        if id_medico is not None:
            query = query.where(SalaEspera.id_medico == id_medico)
        if id_sede is not None:
            query = query.where(SalaEspera.id_sede == id_sede)
        if estado is not None:
            query = query.where(SalaEspera.estado == estado)

        if ordenar_por == "llegada":
            query = query.order_by(SalaEspera.fecha_llegada.asc())
        elif ordenar_por == "turno":
            query = query.order_by(SalaEspera.fecha_turno.asc().nulls_last())
        elif ordenar_por == "prioridad":
            query = query.order_by(SalaEspera.prioridad.desc(), SalaEspera.fecha_llegada.asc())
        else:
            # Por defecto, orden de llegada
            query = query.order_by(SalaEspera.fecha_llegada.asc())

        result = await db.execute(query)
        return list(result.scalars().all())


sala_espera_repo = SalaEsperaRepository()
