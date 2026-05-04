"""Servicio de recetas — lógica de negocio para M3 (Farmacia)."""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_farmacologica import AlertaFarmacologica
from app.models.receta import Receta


async def get_recetas(
    db: AsyncSession,
    estado: Optional[str] = None,
    id_paciente: Optional[int] = None,
    desde_fecha: Optional[date] = None,
) -> list[Receta]:
    """Obtener listado de recetas con filtros opcionales."""
    query = select(Receta)

    if estado:
        query = query.where(Receta.estado == estado)
    if id_paciente:
        query = query.where(Receta.id_paciente == id_paciente)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_receta_by_id(db: AsyncSession, id_receta: int) -> Optional[Receta]:
    """Obtener una receta por su ID."""
    result = await db.execute(select(Receta).where(Receta.id_receta == id_receta))
    return result.scalar_one_or_none()


async def get_alertas_farmacologicas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaFarmacologica]:
    """Obtener alertas farmacológicas de un paciente (Smart Payload)."""
    result = await db.execute(
        select(AlertaFarmacologica).where(
            AlertaFarmacologica.id_paciente == id_paciente
        )
    )
    return list(result.scalars().all())
