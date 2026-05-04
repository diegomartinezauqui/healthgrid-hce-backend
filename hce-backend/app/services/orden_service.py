"""Servicio de órdenes médicas — lógica de negocio para M4/M5 (Estudios)."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinica
from app.models.orden import Orden


async def get_ordenes(
    db: AsyncSession,
    tipo_estudio: str,
    estado: Optional[str] = "Pendiente",
) -> list[Orden]:
    """Obtener listado de órdenes filtrado por tipo y estado."""
    query = select(Orden).where(Orden.tipo_estudio == tipo_estudio)

    if estado:
        query = query.where(Orden.estado == estado)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_orden_by_id(db: AsyncSession, id_orden: int) -> Optional[Orden]:
    """Obtener una orden por su ID."""
    result = await db.execute(select(Orden).where(Orden.id_orden == id_orden))
    return result.scalar_one_or_none()


async def get_alertas_clinicas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinica]:
    """Obtener alertas clínicas de un paciente (Smart Payload)."""
    result = await db.execute(
        select(AlertaClinica).where(AlertaClinica.id_paciente == id_paciente)
    )
    return list(result.scalars().all())
