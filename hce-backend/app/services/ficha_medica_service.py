"""Servicio de ficha médica — lógica de negocio para CRUD de FichaMedica."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha_medica import FichaMedica
from app.repositories.ficha_medica_repository import ficha_medica_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.ficha_medica import FichaMedicaCreate, FichaMedicaUpdate


async def get_ficha_medica(
    db: AsyncSession,
    id_paciente: int,
) -> FichaMedica | None:
    """Obtener la ficha médica de un paciente por su ID."""
    return await ficha_medica_repo.get_by_paciente(db, id_paciente)


async def crear_ficha_medica(
    db: AsyncSession,
    id_paciente: int,
    data: FichaMedicaCreate,
) -> FichaMedica:
    """
    Crear la ficha médica de un paciente.
    Lanza LookupError si el paciente no existe (→ 404).
    Lanza ValueError si ya existe una ficha para ese paciente (→ 409).
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    existente = await ficha_medica_repo.get_by_paciente(db, id_paciente)
    if existente:
        raise ValueError(f"Ya existe una ficha médica para el paciente {id_paciente}.")

    return await ficha_medica_repo.create(db, id_paciente, data)


async def actualizar_ficha_medica(
    db: AsyncSession,
    id_paciente: int,
    data: FichaMedicaUpdate,
) -> FichaMedica | None:
    """
    Actualizar parcialmente la ficha médica de un paciente.
    Solo modifica los campos que vengan con valor (no None).
    Retorna None si la ficha no existe.
    """
    ficha = await ficha_medica_repo.get_by_paciente(db, id_paciente)
    if not ficha:
        return None

    return await ficha_medica_repo.update(db, ficha, data)
