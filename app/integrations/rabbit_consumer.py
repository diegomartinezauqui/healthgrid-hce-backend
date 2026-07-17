"""
Consumer de RabbitMQ — entrada del bus de eventos del Core (M10).

HCE escucha SUS colas (`<base>.requests` y `<base>.responses`) directamente en
RabbitMQ. Los mensajes llegan con el "sobre externo" del Core; el campo `payload`
viene como STRING y hay que parsearlo aparte. Cada evento se despacha a los
servicios existentes (reusando la misma lógica que los webhooks).

Gateado: si `ENABLE_CORE_BUS` es False o faltan credenciales, no se conecta.
Las colas/eventos/bindings se crean con `scripts/setup_core_bus.py`.
"""

import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def start_core_bus_consumer() -> None:
    """Conecta a RabbitMQ y consume las colas de HCE. Pensado para lifespan."""
    if not settings.ENABLE_CORE_BUS:
        logger.info("ℹ️ Core bus deshabilitado (ENABLE_CORE_BUS=False). No se escucha RabbitMQ.")
        return
    if not settings.RABBITMQ_USER or not settings.RABBITMQ_PASSWORD:
        logger.warning("⚠️ Faltan credenciales RabbitMQ; el consumer del Core no arranca.")
        return

    try:
        import aio_pika
    except ImportError:
        logger.error("❌ aio-pika no está instalado; no se puede consumir RabbitMQ.")
        return

    import urllib.parse
    safe_user = urllib.parse.quote_plus(settings.RABBITMQ_USER)
    uri_completa = f"amqp://{safe_user}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}{settings.RABBITMQ_VHOST}"
    uri_enmascarada = f"amqp://{safe_user}:******@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}{settings.RABBITMQ_VHOST}"
    
    logger.warning("🔌 Conectando a RabbitMQ usando URI (Enmascarada): %s", uri_enmascarada)
    logger.warning("🔌 URI Completa de conexión (para validación): %s", uri_completa)

    try:
        connection = await aio_pika.connect_robust(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            login=settings.RABBITMQ_USER,
            password=settings.RABBITMQ_PASSWORD,
            virtualhost=settings.RABBITMQ_VHOST,
        )
    except Exception as exc:
        logger.warning(
            "⚠️ No se pudo conectar a RabbitMQ (el consumer del Core no arranca). "
            "Es normal en local si el usuario '%s' aun no fue registrado en el broker de RabbitMQ: %s",
            settings.RABBITMQ_USER,
            exc
        )
        return

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    colas = [f"{settings.HCE_QUEUE_BASE}.requests", f"{settings.HCE_QUEUE_BASE}.responses"]
    for nombre in colas:
        try:
            # passive=True: la cola ya fue creada vía el Core; solo la referenciamos.
            queue = await channel.declare_queue(nombre, passive=True)
            await queue.consume(_on_message)
            logger.warning("👂 Escuchando cola RabbitMQ: %s", nombre)
        except Exception as exc:  # noqa: BLE001
            logger.warning("⚠️ No se pudo escuchar la cola %s: %s", nombre, exc)

    logger.warning("✅ Consumer del bus del Core inicializado.")


async def _on_message(message) -> None:
    """Procesa un mensaje del Core: parsea sobre + payload y despacha por evento."""
    async with message.process(requeue=False):
        try:
            sobre = json.loads(message.body.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Mensaje del bus no es JSON válido: %s", exc)
            return

        event_name = sobre.get("event_type_name", "")
        payload_raw = sobre.get("payload")
        try:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else (payload_raw or {})
        except Exception:  # noqa: BLE001
            payload = {}

        logger.info("📥 Evento del bus: %s (log_id=%s)", event_name, sobre.get("log_id"))
        try:
            await _dispatch(event_name, payload, sobre)
        except Exception as exc:  # noqa: BLE001
            logger.exception("❌ Error procesando evento %s: %s", event_name, exc)


async def _dispatch(event_name: str, payload: dict, sobre: dict) -> None:
    """Enruta el evento al servicio correspondiente. Reusa la lógica de los webhooks."""
    name = (event_name or "").lower()

    # ── M4 Laboratorio: resultado listo ──
    if "laboratorio" in name and "resultado" in name:
        from app.database import async_session
        from app.schemas.resultado import ResultadoLaboratorioWebhook
        from app.services import resultado_service

        body = ResultadoLaboratorioWebhook(**payload)
        async with async_session() as db:
            await resultado_service.registrar_resultado_laboratorio(db, body)
            await db.commit()
        return

    # ── M5 Imágenes: reporte finalizado ──
    if "imagen" in name and ("reporte" in name or "report" in name or "listo" in name):
        from datetime import datetime
        from app.database import async_session
        from app.schemas.resultado import ResultadoEstudioRequest
        from app.services import resultado_service
        from common.enums.enums_orden import TipoEstudio

        req = ResultadoEstudioRequest(
            id_orden=payload.get("id_orden_hce"),
            id_paciente=payload.get("id_paciente"),
            tipo_estudio=TipoEstudio.IMAGEN,
            id_profesional_firmante=payload.get("profesional_firmante") or "Diagnóstico por Imagen",
            fecha_resultado=datetime.utcnow(),
            informe_resumen=payload.get("informe") or f"Estudio de imagen: {payload.get('titulo', '')}",
            id_externo_estudio=payload.get("report_id"),
        )
        async with async_session() as db:
            await resultado_service.registrar_resultado(db, req)
            await db.commit()
        return

    # ── M2 Turnos: presentismo / check-in ──
    if "presentismo" in name or "checkin" in name or "check_in" in name or ("turno" in name and "llega" in name):
        from app.kafka.handlers.presentismo_handler import handle_presentismo

        await handle_presentismo(payload)
        return

    # ── M6 Camas: ingreso confirmado ──
    if "camas" in name and ("ingreso" in name or "internacion" in name):
        from app.database import async_session
        from app.schemas.internacion import IngresoInternacionRequest
        from app.services import internacion_service

        body = IngresoInternacionRequest(**payload)
        async with async_session() as db:
            await internacion_service.registrar_ingreso(db, body)
            await db.commit()
        return

    # ── M6 Camas: solicitud de cama resuelta (aprobada o rechazada) ──
    # El Core entrega el evento con event_type_name == "SOLICITUD_RESUELTA".
    # Payload esperado de M6:
    #   {
    #     "solicitud_hce_id": <int>,        # id_solicitud en HCE
    #     "decision":         "APROBADA" | "RECHAZADA",
    #     "cama":             "Cama 4"   (solo si APROBADA),
    #     "habitacion":       "Hab 201"  (solo si APROBADA),
    #     "motivo_rechazo":   "..."      (solo si RECHAZADA)
    #   }
    if "solicitud" in name and ("resuelta" in name or "resulta" in name or "resolucion" in name):
        from app.database import async_session
        from app.schemas.solicitud_cama import SolicitudCamaResolver
        from app.services import solicitud_cama_service

        id_solicitud = payload.get("solicitud_hce_id")
        if not id_solicitud:
            logger.error(
                "❌ SOLICITUD_RESUELTA recibida sin 'solicitud_hce_id'. Payload: %s", payload
            )
            return

        # M6 puede enviar la decisión en mayúsculas (APROBADA/RECHAZADA)
        decision_raw = (payload.get("decision") or "").lower()
        decision = "aceptada" if "aprobada" in decision_raw or "aceptada" in decision_raw else "rechazada"

        resolver_body = SolicitudCamaResolver(
            decision=decision,
            cama=payload.get("cama"),
            habitacion=payload.get("habitacion"),
            motivo_rechazo=payload.get("motivo_rechazo"),
        )
        async with async_session() as db:
            try:
                await solicitud_cama_service.resolver_solicitud(db, int(id_solicitud), resolver_body)
                await db.commit()
                logger.info(
                    "✅ Solicitud %s marcada como '%s' por evento SOLICITUD_RESUELTA de M6.",
                    id_solicitud, decision,
                )
            except LookupError as exc:
                logger.error("❌ SOLICITUD_RESUELTA: solicitud %s no encontrada: %s", id_solicitud, exc)
            except ValueError as exc:
                logger.warning("⚠️ SOLICITUD_RESUELTA: no se pudo resolver solicitud %s: %s", id_solicitud, exc)
        return

    logger.warning("🤷 Sin handler para el evento '%s'. Payload: %s", event_name, payload)
