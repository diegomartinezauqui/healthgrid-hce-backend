"""Servicio de episodios — lógica para M7 (Facturación)."""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.acto_medico import ActoMedico
from app.models.episodio import Episodio


async def get_episodios_paciente(
    db: AsyncSession,
    id_paciente: int,
    estado: Optional[str] = None,
    desde_fecha: Optional[date] = None,
    hasta_fecha: Optional[date] = None,
) -> list[Episodio]:
    """Obtener episodios de un paciente con filtros opcionales."""
    query = select(Episodio).where(Episodio.id_paciente == id_paciente)

    if estado and estado != "all":
        query = query.where(Episodio.estado == estado)
    if desde_fecha:
        query = query.where(Episodio.fecha_apertura >= desde_fecha)
    if hasta_fecha:
        query = query.where(Episodio.fecha_apertura <= hasta_fecha)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_episodio_detalle(
    db: AsyncSession, id_paciente: int, id_episodio: int
) -> Optional[Episodio]:
    """Obtener detalle de un episodio con actos médicos."""
    result = await db.execute(
        select(Episodio)
        .options(selectinload(Episodio.actos_medicos))
        .where(
            Episodio.id_episodio == id_episodio,
            Episodio.id_paciente == id_paciente,
        )
    )
    return result.scalar_one_or_none()


async def get_actos_medicos_episodio(
    db: AsyncSession, id_paciente: int, id_episodio: int
) -> list[ActoMedico]:
    """Obtener actos médicos de un episodio específico."""
    # Primero verificar que el episodio pertenece al paciente
    ep_result = await db.execute(
        select(Episodio).where(
            Episodio.id_episodio == id_episodio,
            Episodio.id_paciente == id_paciente,
        )
    )
    if not ep_result.scalar_one_or_none():
        return []

    result = await db.execute(
        select(ActoMedico).where(ActoMedico.id_episodio == id_episodio)
    )
    return list(result.scalars().all())
