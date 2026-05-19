"""Servicio de antecedentes clínicos del paciente."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.antecedente_paciente import AntecedentePaciente
from app.repositories.antecedente_repository import antecedente_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.antecedente import AntecedenteCreate, AntecedenteUpdate


async def get_antecedentes_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AntecedentePaciente]:
    """
    Obtener todos los antecedentes de un paciente (Activos y Resueltos).
    Lanza LookupError si el paciente no existe.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")
    return await antecedente_repo.get_by_paciente(db, id_paciente)


async def crear_antecedente(
    db: AsyncSession,
    id_paciente: int,
    data: AntecedenteCreate,
) -> AntecedentePaciente:
    """
    Registrar un nuevo antecedente para un paciente.
    Lanza LookupError si el paciente no existe.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")
    return await antecedente_repo.create(db, id_paciente, data)


async def actualizar_antecedente(
    db: AsyncSession,
    id_paciente: int,
    id_antecedente: int,
    data: AntecedenteUpdate,
) -> AntecedentePaciente | None:
    """
    Actualización parcial de un antecedente.
    Retorna None si no existe o no pertenece al paciente.
    """
    antecedente = await antecedente_repo.get(db, id_antecedente)
    if not antecedente or antecedente.id_paciente != id_paciente:
        return None
    return await antecedente_repo.update(db, antecedente, data)


async def eliminar_antecedente(
    db: AsyncSession,
    id_paciente: int,
    id_antecedente: int,
) -> bool:
    """
    Eliminar un antecedente. Retorna False si no existe o no pertenece al paciente.
    """
    antecedente = await antecedente_repo.get(db, id_antecedente)
    if not antecedente or antecedente.id_paciente != id_paciente:
        return False
    return await antecedente_repo.delete(db, id_antecedente)
