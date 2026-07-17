"""
Consumidor AMQP (RabbitMQ) del módulo HCE.
Escucha eventos de otros módulos y los delega a los handlers correspondientes.

Topología:
  Exchange  : healthgrid.events  (topic, durable)
  Queue     : hce.presentismo    (durable)
  Binding   : clinica.turnos.presentismo  ← M2 Turnos
"""

import logging

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)

# Routing key del evento que HCE consume
RK_PRESENTISMO = "clinica.turnos.presentismo"
QUEUE_PRESENTISMO = "hce.presentismo"


async def start_amqp_consumer():
    """Conectar a RabbitMQ y empezar a consumir eventos de M2."""
    connection = None
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            settings.AMQP_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        queue = await channel.declare_queue(QUEUE_PRESENTISMO, durable=True)
        await queue.bind(exchange, routing_key=RK_PRESENTISMO)

        logger.info("AMQP consumer escuchando en queue '%s' (binding: %s)", QUEUE_PRESENTISMO, RK_PRESENTISMO)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await _dispatch(message)

    except Exception as e:
        logger.warning("AMQP consumer no disponible: %s", e)
    finally:
        if connection and not connection.is_closed:
            await connection.close()


async def _dispatch(message: aio_pika.IncomingMessage):
    """Ruta el mensaje al handler correcto según el routing key."""
    import json

    routing_key = message.routing_key
    try:
        body = json.loads(message.body.decode("utf-8"))
    except Exception:
        logger.error("AMQP: no se pudo deserializar mensaje en '%s'", routing_key)
        return

    logger.info("AMQP mensaje recibido [%s]: %s", routing_key, body)

    if routing_key == RK_PRESENTISMO:
        from app.kafka.handlers.presentismo_handler import handle_presentismo
        await handle_presentismo(body)
    else:
        logger.warning("AMQP: routing key sin handler registrado: %s", routing_key)
