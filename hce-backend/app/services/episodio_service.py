"""Servicio de episodios — lógica para M7 (Facturación) y HCE."""

import logging
from datetime import date, datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acto_medico import ActoMedico
from app.models.episodio import Episodio
from app.repositories.acto_medico_repository import acto_medico_repo
from app.repositories.episodio_repository import episodio_repo
from app.repositories.paciente_repository import paciente_repo
from app.schemas.episodio import ActoMedicoCreate, EpisodioCreate, EpisodioUpdate
from app.schemas.internacion import SolicitudInternacionRequest
from common.enums.enums_episodio import EstadoEpisodio, TipoEpisodio
from common.enums.enums_kafka import SeveridadPatologia
from app.schemas.kafka_events import (
    EventoKafkaEpisodioCerrado,
    EventoKafkaPatologiaCritica,
)
from app.services.kafka_producer import (
    kafka_producer,
    TOPIC_EPISODIO_CERRADO,
    TOPIC_PATOLOGIA_CRITICA,
)

logger = logging.getLogger(__name__)


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
    solicitud_internacion: Optional[SolicitudInternacionRequest] = None,
    token: Optional[str] = None,
) -> Episodio:
    """
    Abrir un nuevo episodio médico para un paciente.
    Lanza LookupError si el paciente no existe.

    Si el tipo del episodio es 'internacion' y se proporciona una
    `solicitud_internacion`, se realiza una llamada REST sincrónica
    al Módulo 6 (Camas) para solicitar la asignación de cama.
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
    episodio = await episodio_repo.save(db, episodio)

    # Si es un episodio de internación, notificar a M6 para que asigne cama
    if data.tipo == TipoEpisodio.INTERNACION and solicitud_internacion:
        from app.services import m6_client
        try:
            await m6_client.solicitar_internacion(solicitud_internacion, token=token)
        except RuntimeError as exc:
            # Loguear pero no bloquear la creación del episodio
            logger.error(
                "⚠️ No se pudo notificar a M6 la solicitud de internación: %s", exc
            )

    return episodio


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
        # Notificar a M7(Facturacion) y M6(Internacion)
        evento = EventoKafkaEpisodioCerrado(
            id_episodio=id_episodio,
            id_paciente=id_paciente,
            fecha_cierre=episodio.fecha_cierre
        )
        await kafka_producer.publish(TOPIC_EPISODIO_CERRADO, evento.model_dump(mode="json"))

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


async def publicar_patologia_critica(
    id_paciente: int,
    id_episodio: int,
    codigo_patologia: str,
    nombre_patologia: str,
    id_medico_detecta: int,
    id_sede: int,
    severidad: SeveridadPatologia = SeveridadPatologia.HIGH,
) -> None:
    """
    Publicar el evento Kafka clinica.hce.patologia_critica_detectada.

    Debe llamarse cuando se registra un diagnóstico de notificación
    obligatoria (tuberculosis, meningitis, COVID grave, etc.).
    M10 (Core) suscribe este tópico para el bus de auditoría sanitaria.

    Args:
        id_paciente: ID del paciente afectado.
        id_episodio: ID del episodio donde se detectó la patología.
        codigo_patologia: Código CIE-10 o similar (ej. 'A15.0').
        nombre_patologia: Nombre legible (ej. 'Tuberculosis pulmonar').
        id_medico_detecta: ID del médico que registró el diagnóstico.
        id_sede: ID de la sede donde se detectó.
        severidad: Nivel de severidad (moderate, high, critical).
    """
    from uuid import uuid4
    evento = EventoKafkaPatologiaCritica(
        id_evento=uuid4(),
        fecha_ocurrencia=datetime.now(timezone.utc),
        id_paciente=id_paciente,
        id_episodio=id_episodio,
        codigo_patologia=codigo_patologia,
        nombre_patologia=nombre_patologia,
        id_medico_detecta=id_medico_detecta,
        id_sede=id_sede,
        severidad=severidad,
    )
    await kafka_producer.publish(
        TOPIC_PATOLOGIA_CRITICA, evento.model_dump(mode="json")
    )
    logger.info(
        "🚨 Evento patologia_critica publicado — paciente: %s, código: %s, episodio: %s",
        id_paciente,
        codigo_patologia,
        id_episodio,
    )
