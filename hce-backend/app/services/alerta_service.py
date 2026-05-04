"""Servicio de alertas clínicas — lógica para M9 (Monitoreo)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinica


async def get_alertas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinica]:
    """Obtener alertas clínicas del paciente para M9."""
    result = await db.execute(
        select(AlertaClinica).where(AlertaClinica.id_paciente == id_paciente)
    )
    return list(result.scalars().all())
