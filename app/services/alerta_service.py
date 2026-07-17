"""Servicio de alertas clínicas del paciente."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinicaPaciente
from app.repositories.alerta_repository import alerta_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.alerta import AlertaCreate, AlertaUpdate


async def get_alertas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinicaPaciente]:
    """Obtener todas las alertas de un paciente (Activas y Resueltas).
    Lanza LookupError si el paciente no existe.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")
    return await alerta_repo.get_by_paciente(db, id_paciente)


async def get_alertas_activas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinicaPaciente]:
    """Obtener solo alertas Activas — usado para Smart Payload en órdenes y recetas."""
    return await alerta_repo.get_activas_by_paciente(db, id_paciente)


async def crear_alerta(
    db: AsyncSession,
    id_paciente: int,
    data: AlertaCreate,
    id_medico: int,
) -> AlertaClinicaPaciente:
    """
    Registrar una nueva alerta clínica para un paciente.
    Lanza LookupError si el paciente no existe.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")
    return await alerta_repo.create(db, id_paciente, data, id_medico)


async def resolver_alerta(
    db: AsyncSession,
    id_paciente: int,
    id_alerta: int,
    data: AlertaUpdate,
    id_medico: int,
) -> AlertaClinicaPaciente | None:
    """
    Resolver (cerrar) una alerta clínica existente.
    Retorna None si la alerta no existe o no pertenece al paciente.
    """
    alerta = await alerta_repo.get(db, id_alerta)
    if not alerta or alerta.id_paciente != id_paciente:
        return None
    alerta.fecha_resolucion = datetime.now(timezone.utc)
    alerta.id_medico_resolucion = id_medico
    return await alerta_repo.update(db, alerta, data)


async def eliminar_alerta(
    db: AsyncSession,
    id_paciente: int,
    id_alerta: int,
) -> bool:
    """
    Eliminar una alerta. Retorna False si no existe o no pertenece al paciente.
    """
    alerta = await alerta_repo.get(db, id_alerta)
    if not alerta or alerta.id_paciente != id_paciente:
        return False
    return await alerta_repo.delete(db, id_alerta)
