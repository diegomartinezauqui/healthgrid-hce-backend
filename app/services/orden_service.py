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
from common.enums.enums_orden import TipoEstudio, PrioridadOrden, SubtipoEstudio, OrigenOrden

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


async def get_ordenes_paciente(
    db: AsyncSession,
    id_paciente: int,
) -> list[Orden]:
    """Obtener listado de todas las órdenes de un paciente."""
    query = select(Orden).where(Orden.id_paciente == id_paciente).order_by(Orden.fecha_creacion.desc())
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
    id_episodio: Optional[int] = None,
    id_evolucion: Optional[int] = None,
    id_medico_solicitante: Optional[int] = None,
    estudio_ids: Optional[list[int]] = None,
    subtipo: Optional[SubtipoEstudio] = None,
    origen: Optional[OrigenOrden] = OrigenOrden.AMBULATORIO,
    token_auth: Optional[str] = None,
) -> Orden:
    """
    Crear una nueva orden médica de estudio y publicar el evento Kafka
    clinica.estudios.orden_creada para que M4 (Laboratorio) y M5 (Imágenes) la procesen.
    """
    from app.models.paciente import Paciente
    from app.models.episodio import Episodio
    from app.models.evolucion import Evolucion
    
    # Obtener paciente para extraer datos reales (necesarios para el contrato de M4)
    result_p = await db.execute(select(Paciente).where(Paciente.id_paciente == id_paciente))
    paciente = result_p.scalar_one_or_none()
    if not paciente:
        raise LookupError(f"Paciente con ID {id_paciente} no encontrado.")

    # Validar que el episodio exista si se proporcionó
    if id_episodio:
        result_e = await db.execute(select(Episodio).where(Episodio.id_episodio == id_episodio))
        if not result_e.scalar_one_or_none():
            raise LookupError(f"Episodio con ID {id_episodio} no encontrado.")

    # Validar que la evolución exista si se proporcionó
    if id_evolucion:
        result_ev = await db.execute(select(Evolucion).where(Evolucion.id_evolucion == id_evolucion))
        if not result_ev.scalar_one_or_none():
            raise LookupError(f"Evolución con ID {id_evolucion} no encontrada.")

    datos = paciente.datos_personales or {}
    paciente_nombre = datos.get("nombre", "Paciente Desconocido")
    paciente_dni = datos.get("dni", "12345678")
    paciente_edad = datos.get("edad", 30)
    paciente_sexo = datos.get("sexo", "M")

    orden = Orden(
        id_paciente=id_paciente,
        tipo_estudio=tipo_estudio,
        descripcion_pedido=descripcion_pedido,
        prioridad=prioridad,
        estado="Pendiente",
        id_episodio=id_episodio,
        id_evolucion=id_evolucion,
        id_medico_solicitante=id_medico_solicitante,
        subtipo=subtipo,
        estudio_ids=estudio_ids,
        origen=origen,
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

    # Publicar también al bus del Core (RabbitMQ vía POST /events/log). Gateado:
    # no-op si ENABLE_CORE_BUS=False o el event_type_id no está configurado.
    try:
        from app.integrations.core_bus import publish_named
        await publish_named("orden.creada", {
            "id_orden": orden.id_orden,
            "id_orden_hce": orden.id_orden,
            "id_paciente": id_paciente,
            "tipo_estudio": tipo_estudio.value,
            "descripcion": descripcion_pedido,
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("⚠️ No se pudo publicar orden.creada al bus del Core: %s", exc)
    # Integración REST de salida con los módulos M4 y M5
    import asyncio
    from app.integrations import m4_client, m5_client
    
    if tipo_estudio == TipoEstudio.LABORATORIO:
        # Obtener alertas clínicas del paciente para el Smart Payload de M4
        alertas = await alerta_repo.get_activas_by_paciente(db, id_paciente)
        alertas_payload = [
            {"tipo": a.tipo, "severidad": a.severidad, "descripcion": a.descripcion}
            for a in alertas
        ]
        asyncio.create_task(
            m4_client.notificar_orden_hce(
                id_orden=orden.id_orden,
                id_paciente=id_paciente,
                descripcion_pedido=descripcion_pedido,
                prioridad=prioridad.value if hasattr(prioridad, "value") else str(prioridad),
                paciente_nombre=paciente_nombre,
                paciente_dni=paciente_dni,
                paciente_edad=int(paciente_edad) if paciente_edad else 0,
                paciente_sexo=paciente_sexo,
                alertas_clinicas=alertas_payload,
                estudio_ids=estudio_ids,
                token_auth=token_auth,
            )
        )
    elif tipo_estudio == TipoEstudio.IMAGEN:
        asyncio.create_task(
            m5_client.notificar_orden(
                id_orden=orden.id_orden,
                id_paciente=id_paciente,
                descripcion=descripcion_pedido,
                subtipo=subtipo.value if subtipo and hasattr(subtipo, "value") else str(subtipo) if subtipo else None,
                token_auth=token_auth,
            )
        )

    return orden
