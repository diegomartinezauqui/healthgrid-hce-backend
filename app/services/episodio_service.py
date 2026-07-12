"""Servicio de episodios — lógica para M7 (Facturación) y HCE."""

import logging
from datetime import date, datetime, timezone
from typing import Optional, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acto_medico import ActoMedico
from app.models.cobertura_medica import CoberturaMedica
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
        
        # Publicar también al bus del Core (RabbitMQ vía POST /events/log)
        try:
            from app.integrations.core_bus import publish_named
            await publish_named("episodio.cerrado", {
                "id_episodio": id_episodio,
                "id_paciente": id_paciente,
                "id_sede": episodio.id_sede,
                "tipo_episodio": episodio.tipo.value if hasattr(episodio.tipo, "value") else episodio.tipo,
                "id_medico_cierre": episodio.id_medico_responsable,
                "total_actos_medicos": len(episodio.actos_medicos),
                "fecha_cierre": episodio.fecha_cierre.isoformat(),
            })
        except Exception as exc:
            logger.warning("⚠️ No se pudo publicar episodio.cerrado al bus del Core: %s", exc)

        # Notificar a M7(Facturacion) y M6(Internacion) vía Kafka (mantener por compatibilidad)
        try:
            evento = EventoKafkaEpisodioCerrado(
                id_evento=uuid4(),
                fecha_ocurrencia=episodio.fecha_cierre,
                id_episodio=id_episodio,
                id_paciente=id_paciente,
                id_sede=episodio.id_sede,
                tipo_episodio=episodio.tipo,
                id_medico_cierre=episodio.id_medico_responsable,
                total_actos_medicos=len(episodio.actos_medicos),
            )
            await kafka_producer.publish(TOPIC_EPISODIO_CERRADO, evento.model_dump(mode="json"))
        except Exception as e:
            logger.warning("⚠️ No se pudo publicar episodio_cerrado a Kafka: %s", e)

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

    id_profesional_final = data.id_profesional or id_profesional_default
    fecha_realizacion_final = data.fecha_realizacion or datetime.now(timezone.utc)

    acto = ActoMedico(
        id_episodio=id_episodio,
        codigo_nomenclador=data.codigo_nomenclador,
        descripcion=data.descripcion,
        tipo=data.tipo.value,  # Guardar el valor string del enum
        id_profesional=id_profesional_final,
        fecha_realizacion=fecha_realizacion_final,
        cantidad=data.cantidad,
        observaciones=data.observaciones,
    )
    acto = await acto_medico_repo.save(db, acto)

    # ── Notificar a M7 (Facturación) si el acto tiene código de nomenclador ──
    # Solo actos con codigo_nomenclador son facturables. Se busca la cobertura
    # vigente del paciente para obtener planId y número de afiliado.
    # El error no bloquea: si M7 no está disponible el acto médico igual se guarda.
    if acto.codigo_nomenclador:
        await _notificar_m7(
            db=db,
            acto=acto,
            id_paciente=id_paciente,
            id_episodio=id_episodio,
            id_profesional=id_profesional_final,
            fecha_realizacion=fecha_realizacion_final,
        )

    return acto


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
    # Publicar al bus del Core (RabbitMQ)
    try:
        from app.integrations.core_bus import publish_named
        await publish_named("notificacion.obligatoria", {
            "id_paciente": id_paciente,
            "id_episodio": id_episodio,
            "codigo_patologia": codigo_patologia,
            "nombre_patologia": nombre_patologia,
            "id_medico_detecta": id_medico_detecta,
            "id_sede": id_sede,
            "severidad": severidad,
            "fecha_ocurrencia": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("⚠️ No se pudo publicar notificacion.obligatoria al bus del Core: %s", exc)

    # Mantenemos Kafka por compatibilidad
    try:
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
    except Exception as e:
        logger.warning("⚠️ No se pudo publicar patologia_critica a Kafka: %s", e)
    logger.info(
        "🚨 Evento patologia_critica publicado — paciente: %s, código: %s, episodio: %s",
        id_paciente,
        codigo_patologia,
        id_episodio,
    )


async def _notificar_m7(
    db: AsyncSession,
    acto: ActoMedico,
    id_paciente: int,
    id_episodio: int,
    id_profesional: int,
    fecha_realizacion: datetime,
) -> None:
    """
    Busca la cobertura médica vigente del paciente y llama a m7_client
    para registrar el acto como prestación facturable en M7.

    Si M7 no está disponible o el paciente no tiene cobertura registrada,
    se loguea el problema pero NO se lanza excepción: el acto médico
    ya fue persistido y no debe verse afectado por fallas del módulo externo.
    """
    from app.services import m7_client

    # Obtener cobertura vigente (la más reciente)
    result = await db.execute(
        select(CoberturaMedica)
        .where(CoberturaMedica.id_paciente == id_paciente)
        .order_by(CoberturaMedica.vigente_desde.desc())
        .limit(1)
    )
    cobertura = result.scalar_one_or_none()

    if not cobertura:
        logger.warning(
            "⚠️ [M7] Acto médico %s con código nomenclador registrado, "
            "pero el paciente %s no tiene cobertura médica cargada. "
            "No se notificó a Facturación.",
            acto.id_acto_medico,
            id_paciente,
        )
        return

    try:
        await m7_client.notificar_prestacion(
            id_paciente=id_paciente,
            id_episodio=id_episodio,
            id_acto_medico=acto.id_acto_medico,
            id_profesional=id_profesional,
            plan_id=cobertura.id_obra_social,
            codigo_prestacion=acto.codigo_nomenclador,
            numero_afiliado=cobertura.numero_afiliado,
            fecha_atencion=fecha_realizacion.isoformat(),
            cantidad=acto.cantidad,
            observaciones=acto.observaciones,
        )
    except RuntimeError as exc:
        # M7 no disponible o rechazó la llamada — se loguea, no bloquea
        logger.error(
            "❌ [M7] No se pudo notificar la prestación del acto %s a Facturación: %s",
            acto.id_acto_medico,
            exc,
        )
