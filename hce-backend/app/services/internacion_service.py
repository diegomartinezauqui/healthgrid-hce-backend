"""Servicio de internación — lógica para M6 (Camas)."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episodio import Episodio
from app.models.movimiento_internacion import MovimientoInternacion
from app.models.solicitud_cama import SolicitudCama
from app.schemas.internacion import IngresoInternacionRequest


from common.enums.enums_episodio import EstadoEpisodio, TipoEpisodio


async def registrar_ingreso(
    db: AsyncSession,
    data: IngresoInternacionRequest,
) -> dict:
    """
    Registrar el ingreso de un paciente notificado por M6.

    Si M6 reenvía el `id_episodio` de origen, ese MISMO episodio pasa a
    internación (no se crea uno nuevo). Si no lo reenvía, se crea un episodio
    de internación nuevo (compatibilidad hacia atrás).
    En ambos casos se registra el movimiento de internación con la cama asignada.
    """
    if data.id_episodio is not None:
        # 1a. El episodio existente pasa a internación
        episodio = await db.get(Episodio, data.id_episodio)
        if episodio is None:
            raise LookupError(
                f"Episodio {data.id_episodio} no encontrado para registrar el ingreso."
            )
        if episodio.id_paciente != data.id_paciente:
            raise ValueError(
                "El episodio indicado no pertenece al paciente del ingreso."
            )
        episodio.tipo = TipoEpisodio.INTERNACION
        episodio.estado = EstadoEpisodio.OPEN
        await db.flush()
    else:
        # 1b. Sin episodio de origen: se crea uno de internación
        episodio = Episodio(
            id_paciente=data.id_paciente,
            tipo=TipoEpisodio.INTERNACION,
            estado=EstadoEpisodio.OPEN,
            id_sede=1,  # Se podría obtener del contexto o usar sede por defecto
            id_medico_responsable=0,
            fecha_apertura=data.fecha_ingreso,
        )
        db.add(episodio)
        await db.flush()  # Para obtener el id_episodio generado

    # 2. Buscar y cerrar la solicitud de cama pendiente para este episodio si existe
    q_sol = await db.execute(
        select(SolicitudCama).where(
            SolicitudCama.id_episodio == episodio.id_episodio,
            SolicitudCama.estado == "pendiente",
        )
    )
    solicitud = q_sol.scalar_one_or_none()
    if solicitud:
        solicitud.estado = "aceptada"
        solicitud.cama = data.cama
        solicitud.habitacion = data.habitacion
        solicitud.fecha_resolucion = datetime.utcnow()

    # 3. Crear movimiento de internación
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
    await db.commit()

    return {
        "id_episodio": episodio.id_episodio,
        "id_movimiento": movimiento.id_movimiento,
    }
