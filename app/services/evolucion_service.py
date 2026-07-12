"""Servicio de evoluciones médicas — lógica de negocio."""

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolucion import Evolucion
from app.repositories.episodio_repository import episodio_repo
from app.repositories.evolucion_repository import evolucion_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.evolucion import EvolucionCreate, EvolucionUpdate
from common.enums.enums_episodio import EstadoEpisodio


async def get_evoluciones_episodio(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
) -> Sequence[Evolucion]:
    """
    Obtener todas las evoluciones de un episodio específico.
    Verifica que el paciente exista y que el episodio le pertenezca.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        raise LookupError(
            f"No existe el episodio con id {id_episodio} para el paciente {id_paciente}."
        )

    return await evolucion_repo.get_by_episodio(db, id_episodio)


async def get_evolucion_detalle(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
    id_evolucion: int,
) -> Optional[Evolucion]:
    """Obtener el detalle de una evolución específica."""
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        raise LookupError(
            f"No existe el episodio con id {id_episodio} para el paciente {id_paciente}."
        )

    return await evolucion_repo.get_by_episodio_and_id(db, id_episodio, id_evolucion)


async def registrar_evolucion(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
    data: EvolucionCreate,
    id_profesional: int,
) -> Evolucion:
    """
    Registra una nueva evolución médica dentro de un episodio activo.
    Lanza LookupError si el episodio no pertenece al paciente.
    Lanza ValueError si el episodio está cerrado.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        raise LookupError(
            f"No existe el episodio con id {id_episodio} para el paciente {id_paciente}."
        )

    if episodio.estado == EstadoEpisodio.CLOSED:
        raise ValueError("No se pueden registrar evoluciones en un episodio cerrado.")

    evolucion = Evolucion(
        id_episodio=id_episodio,
        id_profesional=id_profesional,
        contenido=data.contenido,
        fecha=data.fecha or datetime.now(timezone.utc),
    )
    return await evolucion_repo.save(db, evolucion)


async def actualizar_evolucion(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
    id_evolucion: int,
    data: EvolucionUpdate,
) -> Optional[Evolucion]:
    """
    Actualiza parcialmente una evolución médica existente.
    Retorna None si la evolución no existe o no pertenece al episodio/paciente.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        raise LookupError(
            f"No existe el episodio con id {id_episodio} para el paciente {id_paciente}."
        )

    evolucion = await evolucion_repo.get_by_episodio_and_id(
        db, id_episodio, id_evolucion
    )
    if not evolucion:
        return None

    return await evolucion_repo.update(db, evolucion, data)
