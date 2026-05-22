"""Servicio de episodios — lógica para M7 (Facturación) y HCE."""

from datetime import date, datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acto_medico import ActoMedico
from app.models.episodio import Episodio
from app.repositories.acto_medico_repository import acto_medico_repo
from app.repositories.episodio_repository import episodio_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.episodio import ActoMedicoCreate, EpisodioCreate, EpisodioUpdate
from common.enums.enums_episodio import EstadoEpisodio


async def get_episodios_paciente(
    db: AsyncSession,
    id_paciente: int,
    estado: Optional[str] = None,
    desde_fecha: Optional[date] = None,
    hasta_fecha: Optional[date] = None,
) -> Sequence[Episodio]:
    """Obtener episodios de un paciente con filtros opcionales."""
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")
    return await episodio_repo.get_by_paciente(
        db, id_paciente, estado=estado, desde_fecha=desde_fecha, hasta_fecha=hasta_fecha
    )


async def get_episodio_detalle(
    db: AsyncSession, id_paciente: int, id_episodio: int
) -> Optional[Episodio]:
    """Obtener detalle de un episodio con actos médicos."""
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")
    return await episodio_repo.get_detalle(db, id_paciente, id_episodio)


async def get_actos_medicos_episodio(
    db: AsyncSession, id_paciente: int, id_episodio: int
) -> Sequence[ActoMedico]:
    """Obtener actos médicos de un episodio específico."""
    # Primero verificar que el episodio pertenece al paciente
    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        return []

    return await acto_medico_repo.get_by_episodio(db, id_episodio)


async def abrir_episodio(
    db: AsyncSession,
    id_paciente: int,
    data: EpisodioCreate,
    id_medico: int,
    id_sede: int,
) -> Episodio:
    """
    Abrir un nuevo episodio médico para un paciente.
    Lanza LookupError si el paciente no existe.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    episodio = Episodio(
        id_paciente=id_paciente,
        tipo=data.tipo,
        estado=EstadoEpisodio.OPEN,
        id_sede=id_sede,
        id_medico_responsable=id_medico,
        diagnostico_principal=data.diagnostico_principal,
        fecha_apertura=datetime.now(timezone.utc),
    )
    return await episodio_repo.save(db, episodio)


async def actualizar_episodio(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
    data: EpisodioUpdate,
) -> Optional[Episodio]:
    """
    Actualiza parcialmente un episodio médico existente.
    Si se solicita cerrar (estado == CLOSED), se registra la fecha_cierre.
    """
    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        return None

    # Lógica especial si se está cerrando el episodio
    if data.estado == EstadoEpisodio.CLOSED and episodio.estado != EstadoEpisodio.CLOSED:
        episodio.fecha_cierre = datetime.now(timezone.utc)

    return await episodio_repo.update(db, episodio, data)


async def registrar_acto_medico(
    db: AsyncSession,
    id_paciente: int,
    id_episodio: int,
    data: ActoMedicoCreate,
    id_profesional_default: int,
) -> ActoMedico:
    """
    Registra un acto médico dentro de un episodio activo.
    Lanza LookupError si el episodio no pertenece al paciente.
    Lanza ValueError si el episodio está cerrado.
    """
    episodio = await episodio_repo.get(db, id_episodio)
    if not episodio or episodio.id_paciente != id_paciente:
        raise LookupError(f"No existe el episodio con id {id_episodio} para el paciente {id_paciente}.")

    if episodio.estado == EstadoEpisodio.CLOSED:
        raise ValueError("No se pueden registrar actos médicos en un episodio cerrado.")

    acto = ActoMedico(
        id_episodio=id_episodio,
        codigo_nomenclador=data.codigo_nomenclador,
        descripcion=data.descripcion,
        tipo=data.tipo.value,  # Guardar el valor string del enum
        id_profesional=data.id_profesional or id_profesional_default,
        fecha_realizacion=data.fecha_realizacion or datetime.now(timezone.utc),
        cantidad=data.cantidad,
        observaciones=data.observaciones,
    )
    return await acto_medico_repo.save(db, acto)
