"""Servicio de recetas — lógica de negocio para M3 (Farmacia)."""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinicaPaciente
from app.models.receta import Receta
from app.repositories.alerta_repository import alerta_repo
from app.schemas.kafka_events import EventoKafkaNuevaReceta
from app.services.kafka_producer import kafka_producer, TOPIC_RECETA_CREADA
from common.enums.enums_receta import EstadoReceta

logger = logging.getLogger(__name__)


async def get_recetas(
    db: AsyncSession,
    estado: Optional[str] = None,
    id_paciente: Optional[int] = None,
    desde_fecha: Optional[date] = None,
) -> list[Receta]:
    """Obtener listado de recetas con filtros opcionales."""
    query = select(Receta)

    if estado:
        query = query.where(Receta.estado == estado)
    if id_paciente:
        query = query.where(Receta.id_paciente == id_paciente)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_receta_by_id(db: AsyncSession, id_receta: int) -> Optional[Receta]:
    """Obtener una receta por su ID."""
    result = await db.execute(select(Receta).where(Receta.id_receta == id_receta))
    return result.scalar_one_or_none()


async def get_alertas_farmacologicas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinicaPaciente]:
    """Obtener alertas activas del paciente para Smart Payload en recetas."""
    return await alerta_repo.get_activas_by_paciente(db, id_paciente)


async def crear_receta(
    db: AsyncSession,
    id_paciente: int,
    medicamento: str,
    tipo_paciente: str = "Ambulatorio",
    id_evolucion: Optional[int] = None,
    indicaciones: Optional[str] = None,
) -> Receta:
    """
    Crear una nueva receta electrónica y publicar el evento Kafka
    clinica.farmacia.receta_creada para que M3 (Farmacia) la procese.

    Args:
        db: Sesión de base de datos.
        id_paciente: ID del paciente al que se receta.
        medicamento: Nombre y dosis del medicamento.
        tipo_paciente: 'Internado' o 'Ambulatorio' (default Ambulatorio).
        id_evolucion: ID de la evolución médica de origen (opcional).
        indicaciones: Instrucciones de administración (opcional).

    Returns:
        Receta recién creada y persistida.
    """
    receta = Receta(
        id_paciente=id_paciente,
        medicamento=medicamento,
        estado=EstadoReceta.ACTIVA,
        id_evolucion=id_evolucion,
        indicaciones=indicaciones,
    )
    db.add(receta)
    await db.flush()  # Para obtener el id_receta generado

    # Publicar evento Kafka → M3 (Farmacia)
    evento = EventoKafkaNuevaReceta(
        id_receta=receta.id_receta,
        tipo_paciente=tipo_paciente,
    )
    await kafka_producer.publish(TOPIC_RECETA_CREADA, evento.model_dump(mode="json"))
    logger.info(
        "📤 Evento receta_creada publicado — receta: %s, paciente: %s",
        receta.id_receta,
        id_paciente,
    )

    return receta
