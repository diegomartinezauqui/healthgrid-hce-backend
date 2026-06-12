"""Servicio de órdenes médicas — lógica de negocio para M4/M5 (Estudios)."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinicaPaciente
from app.models.orden import Orden
from app.repositories.alerta_repository import alerta_repo
from app.schemas.kafka_events import EventoKafkaNuevaOrden
from app.services.kafka_producer import kafka_producer, TOPIC_ORDEN_CREADA
from common.enums.enums_orden import TipoEstudio, PrioridadOrden

logger = logging.getLogger(__name__)


async def get_ordenes(
    db: AsyncSession,
    tipo_estudio: str,
    estado: Optional[str] = "Pendiente",
) -> list[Orden]:
    """Obtener listado de órdenes filtrado por tipo y estado."""
    query = select(Orden).where(Orden.tipo_estudio == tipo_estudio)

    if estado:
        query = query.where(Orden.estado == estado)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_orden_by_id(db: AsyncSession, id_orden: int) -> Optional[Orden]:
    """Obtener una orden por su ID."""
    result = await db.execute(select(Orden).where(Orden.id_orden == id_orden))
    return result.scalar_one_or_none()


async def get_alertas_clinicas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinicaPaciente]:
    """Obtener alertas activas del paciente para Smart Payload en órdenes."""
    return await alerta_repo.get_activas_by_paciente(db, id_paciente)


async def crear_orden(
    db: AsyncSession,
    id_paciente: int,
    tipo_estudio: TipoEstudio,
    descripcion_pedido: Optional[str] = None,
    prioridad: PrioridadOrden = PrioridadOrden.NORMAL,
) -> Orden:
    """
    Crear una nueva orden médica de estudio y publicar el evento Kafka
    clinica.estudios.orden_creada para que M4 (Laboratorio) y M5 (Imágenes) la procesen.

    Args:
        db: Sesión de base de datos.
        id_paciente: ID del paciente.
        tipo_estudio: Tipo de estudio (Laboratorio, Imagen, Anatomia_Patologica).
        descripcion_pedido: Descripción del estudio requerido (opcional).
        prioridad: Prioridad de la orden (Normal, Urgente, Emergencia).

    Returns:
        Orden recién creada y persistida.
    """
    orden = Orden(
        id_paciente=id_paciente,
        tipo_estudio=tipo_estudio,
        descripcion_pedido=descripcion_pedido,
        prioridad=prioridad,
        estado="Pendiente",
    )
    db.add(orden)
    await db.flush()  # Para obtener el id_orden generado

    # Publicar evento Kafka → M4 (Laboratorio) / M5 (Imágenes)
    evento = EventoKafkaNuevaOrden(
        id_orden=orden.id_orden,
        tipo_estudio=tipo_estudio,
    )
    await kafka_producer.publish(TOPIC_ORDEN_CREADA, evento.model_dump(mode="json"))
    logger.info(
        "📤 Evento orden_creada publicado — orden: %s, tipo: %s, paciente: %s",
        orden.id_orden,
        tipo_estudio.value,
        id_paciente,
    )

    return orden
