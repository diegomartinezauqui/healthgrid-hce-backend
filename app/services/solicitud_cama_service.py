"""Servicio de solicitudes de cama (internación / pase) — integración M6 (Camas).

Persiste la solicitud y su estado. La "resolución" simula la respuesta de M6:
al aceptar, registra la cama asignada y crea el movimiento de internación; si es
una internación, el episodio pasa a tipo=internacion.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episodio import Episodio
from app.models.movimiento_internacion import MovimientoInternacion
from app.models.solicitud_cama import SolicitudCama
from app.schemas.solicitud_cama import SolicitudCamaCreate, SolicitudCamaResolver
from common.enums.enums_episodio import EstadoEpisodio, TipoEpisodio


async def crear_solicitud(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
    body: SolicitudCamaCreate,
) -> SolicitudCama:
    """Crea una solicitud pendiente. Rechaza si ya hay otra pendiente en el episodio."""
    episodio = await db.get(Episodio, id_episodio)
    if episodio is None or episodio.id_paciente != id_paciente:
        raise LookupError("Episodio no encontrado para este paciente.")

    pendientes = await db.execute(
        select(SolicitudCama).where(
            SolicitudCama.id_episodio == id_episodio,
            SolicitudCama.estado == "pendiente",
        )
    )
    if pendientes.scalars().first() is not None:
        raise ValueError("Ya existe una solicitud de cama pendiente para este episodio.")

    solicitud = SolicitudCama(
        id_paciente=id_paciente,
        id_episodio=id_episodio,
        tipo=body.tipo,
        prioridad=body.prioridad,
        sector=body.sector,
        motivo=body.motivo,
        estado="pendiente",
    )
    db.add(solicitud)
    await db.flush()
    return solicitud


async def listar_por_episodio(db: AsyncSession, id_episodio: int) -> list[SolicitudCama]:
    result = await db.execute(
        select(SolicitudCama)
        .where(SolicitudCama.id_episodio == id_episodio)
        .order_by(SolicitudCama.fecha_solicitud.desc())
    )
    return list(result.scalars().all())


async def get_cama_actual(db: AsyncSession, id_episodio: int) -> Optional[MovimientoInternacion]:
    """Último movimiento de internación del episodio (cama actual)."""
    result = await db.execute(
        select(MovimientoInternacion)
        .where(MovimientoInternacion.id_episodio == id_episodio)
        .order_by(MovimientoInternacion.fecha_ingreso.desc(), MovimientoInternacion.id_movimiento.desc())
    )
    return result.scalars().first()


async def resolver_solicitud(
    db: AsyncSession,
    id_solicitud: int,
    body: SolicitudCamaResolver,
) -> SolicitudCama:
    """Simula la respuesta de M6: acepta (con cama) o rechaza la solicitud."""
    solicitud = await db.get(SolicitudCama, id_solicitud)
    if solicitud is None:
        raise LookupError(f"Solicitud {id_solicitud} no encontrada.")
    if solicitud.estado != "pendiente":
        raise ValueError(f"La solicitud ya está {solicitud.estado}; no se puede resolver.")

    solicitud.fecha_resolucion = datetime.utcnow()

    if body.decision == "rechazada":
        solicitud.estado = "rechazada"
        solicitud.motivo_rechazo = body.motivo_rechazo
        await db.flush()
        return solicitud

    solicitud.estado = "aceptada"
    if body.cama:
        solicitud.cama = body.cama
        solicitud.habitacion = body.habitacion

        # Si es internación inicial, el MISMO episodio pasa a internación
        if solicitud.tipo == "internacion":
            episodio = await db.get(Episodio, solicitud.id_episodio)
            if episodio is not None:
                episodio.tipo = TipoEpisodio.INTERNACION
                episodio.estado = EstadoEpisodio.OPEN

        # Tanto internación como pase generan un movimiento de cama
        movimiento = MovimientoInternacion(
            id_episodio=solicitud.id_episodio,
            id_paciente=solicitud.id_paciente,
            sector=solicitud.sector or "Sin especificar",
            habitacion=body.habitacion,
            cama=body.cama,
            fecha_ingreso=datetime.utcnow(),
            medico_solicitante="M6 (Camas)",
        )
        db.add(movimiento)
    else:
        # Si no viene cama aún, simplemente marcamos como aceptada administrativamente
        if solicitud.tipo == "internacion":
            episodio = await db.get(Episodio, solicitud.id_episodio)
            if episodio is not None:
                episodio.tipo = TipoEpisodio.INTERNACION
                episodio.estado = EstadoEpisodio.OPEN
    await db.flush()
    return solicitud


async def cancelar_solicitud(db: AsyncSession, id_solicitud: int) -> SolicitudCama:
    solicitud = await db.get(SolicitudCama, id_solicitud)
    if solicitud is None:
        raise LookupError(f"Solicitud {id_solicitud} no encontrada.")
    if solicitud.estado != "pendiente":
        raise ValueError(f"La solicitud ya está {solicitud.estado}; no se puede cancelar.")
    solicitud.estado = "cancelada"
    solicitud.fecha_resolucion = datetime.utcnow()
    await db.flush()
    return solicitud
