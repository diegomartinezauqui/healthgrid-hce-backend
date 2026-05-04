"""Servicio de resultados de estudios — lógica para M4/M5 → HCE."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resultado import Resultado
from app.schemas.resultado import ResultadoEstudioRequest


async def registrar_resultado(
    db: AsyncSession,
    data: ResultadoEstudioRequest,
) -> Resultado:
    """Registrar un resultado de estudio en la HCE."""
    resultado = Resultado(
        id_orden=data.id_orden,
        id_paciente=data.id_paciente,
        tipo_estudio=data.tipo_estudio.value,
        id_profesional_firmante=data.id_profesional_firmante,
        fecha_resultado=data.fecha_resultado,
        informe_resumen=data.informe_resumen,
        id_externo_estudio=data.id_externo_estudio,
    )
    db.add(resultado)
    await db.flush()
    return resultado


async def get_resultados_paciente(
    db: AsyncSession, id_paciente: int
) -> list[Resultado]:
    """Obtener todos los resultados de un paciente (para M8 Portal)."""
    result = await db.execute(
        select(Resultado).where(Resultado.id_paciente == id_paciente)
    )
    return list(result.scalars().all())
