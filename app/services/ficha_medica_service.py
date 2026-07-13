"""Servicio de ficha médica — lógica de negocio para CRUD de FichaMedica."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha_medica import FichaMedica
from app.repositories.ficha_medica_repository import ficha_medica_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.ficha_medica import (
    FichaMedicaCreate,
    FichaMedicaUpdate,
    FichaMedicaCompletaCreate,
    FichaMedicaCompletaResponse,
    FichaMedicaSchema,
)
from app.schemas.antecedente import AntecedenteSchema
from app.schemas.alerta import AlertaSchema
from app.services import antecedente_service, alerta_service


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


async def crear_ficha_medica_completa(
    db: AsyncSession,
    id_paciente: int,
    data: FichaMedicaCompletaCreate,
    id_medico: int,
) -> FichaMedicaCompletaResponse:
    """
    Registrar/actualizar de forma atómica la ficha médica, los antecedentes y las alertas clínicas de un paciente.
    Reutiliza los servicios correspondientes para aprovechar sus validaciones.
    Sincroniza además los datos demográficos (dni, fecha_nacimiento, genero, obra_social) en el paciente.
    """
    # 0. Validar paciente y actualizar datos demográficos locales
    paciente = await paciente_repo.get(db, id_paciente)
    if not paciente:
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    datos = paciente.datos_personales or {}
    updated = False
    if data.dni is not None:
        datos["dni"] = data.dni
        updated = True
    if data.fecha_nacimiento is not None:
        datos["fecha_nacimiento"] = data.fecha_nacimiento
        updated = True
    if data.genero is not None:
        datos["genero"] = data.genero
        updated = True
    if data.obra_social is not None:
        datos["obra_social"] = data.obra_social
        updated = True

    if updated:
        from sqlalchemy.orm.attributes import flag_modified
        paciente.datos_personales = datos
        flag_modified(paciente, "datos_personales")
        db.add(paciente)

    # 1. Crear o actualizar ficha médica básica
    ficha = await ficha_medica_repo.get_by_paciente(db, id_paciente)
    if not ficha:
        ficha = await ficha_medica_repo.create(db, id_paciente, data.ficha_medica)
    else:
        update_data = FichaMedicaUpdate(
            grupo_sanguineo=data.ficha_medica.grupo_sanguineo,
            peso_kg=data.ficha_medica.peso_kg,
            altura_cm=data.ficha_medica.altura_cm,
            observaciones_generales=data.ficha_medica.observaciones_generales,
        )
        ficha = await ficha_medica_repo.update(db, ficha, update_data)

    # Limpiar antecedentes y alertas previas del paciente en base de datos para reemplazo atómico
    from app.models.antecedente_paciente import AntecedentePaciente
    from app.models.alerta_clinica import AlertaClinicaPaciente
    from sqlalchemy import delete
    await db.execute(delete(AntecedentePaciente).where(AntecedentePaciente.id_paciente == id_paciente))
    await db.execute(delete(AlertaClinicaPaciente).where(AlertaClinicaPaciente.id_paciente == id_paciente))

    # 2. Registrar Antecedentes
    antecedentes_creados = []
    for ant_data in data.antecedentes:
        antecedente = await antecedente_service.crear_antecedente(
            db, id_paciente, ant_data, id_medico
        )
        antecedentes_creados.append(antecedente)

    # 3. Registrar Alertas Clínicas
    alertas_creadas = []
    for alert_data in data.alertas_clinicas:
        alerta = await alerta_service.crear_alerta(
            db, id_paciente, alert_data, id_medico
        )
        alertas_creadas.append(alerta)

    return FichaMedicaCompletaResponse(
        ficha_medica=FichaMedicaSchema.model_validate(ficha),
        antecedentes=[AntecedenteSchema.model_validate(a) for a in antecedentes_creados],
        alertas_clinicas=[AlertaSchema.model_validate(a) for a in alertas_creadas],
    )

