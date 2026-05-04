"""Servicio de internación — lógica para M6 (Camas)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episodio import Episodio
from app.models.movimiento_internacion import MovimientoInternacion
from app.schemas.internacion import IngresoInternacionRequest


async def registrar_ingreso(
    db: AsyncSession,
    data: IngresoInternacionRequest,
) -> dict:
    """
    Registrar el ingreso de un paciente notificado por M6.
    Crea un episodio de internación + movimiento de internación.
    """
    # 1. Crear episodio de internación
    episodio = Episodio(
        id_paciente=data.id_paciente,
        tipo="internacion",
        estado="open",
        id_sede=0,  # Se podría obtener del contexto del usuario
        id_medico_responsable=0,  # Idem
        fecha_apertura=data.fecha_ingreso,
    )
    db.add(episodio)
    await db.flush()  # Para obtener el id_episodio generado

    # 2. Crear movimiento de internación
    movimiento = MovimientoInternacion(
        id_episodio=episodio.id_episodio,
        id_paciente=data.id_paciente,
        sector=data.sector,
        habitacion=data.habitacion,
        cama=data.cama,
        fecha_ingreso=data.fecha_ingreso,
        medico_solicitante=data.medico_solicitante,
    )
    db.add(movimiento)
    await db.flush()

    return {
        "id_episodio": episodio.id_episodio,
        "id_movimiento": movimiento.id_movimiento,
    }
