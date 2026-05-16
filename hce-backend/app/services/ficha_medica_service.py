"""Servicio de ficha médica — lógica de negocio para CRUD de FichaMedica."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha_medica import FichaMedica
from app.schemas.ficha_medica import FichaMedicaCreate, FichaMedicaUpdate


async def get_ficha_medica(
    db: AsyncSession,
    id_paciente: int,
) -> FichaMedica | None:
    """Obtener la ficha médica de un paciente por su ID."""
    result = await db.execute(
        select(FichaMedica).where(FichaMedica.id_paciente == id_paciente)
    )
    return result.scalar_one_or_none()


async def crear_ficha_medica(
    db: AsyncSession,
    id_paciente: int,
    data: FichaMedicaCreate,
) -> FichaMedica:
    """
    Crear la ficha médica de un paciente.
    Lanza ValueError si ya existe una ficha para ese paciente.
    """
    existente = await get_ficha_medica(db, id_paciente)
    if existente:
        raise ValueError(f"Ya existe una ficha médica para el paciente {id_paciente}.")

    ficha = FichaMedica(
        id_paciente=id_paciente,
        grupo_sanguineo=data.grupo_sanguineo,
        peso_kg=data.peso_kg,
        altura_cm=data.altura_cm,
        observaciones_generales=data.observaciones_generales,
    )
    db.add(ficha)
    await db.flush()  # Persiste sin cerrar la transacción; el commit lo hace el dependency get_db
    return ficha


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
    ficha = await get_ficha_medica(db, id_paciente)
    if not ficha:
        return None

    # Actualización parcial: solo se pisan los campos que el cliente envió
    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(ficha, campo, valor)

    await db.flush()
    return ficha
