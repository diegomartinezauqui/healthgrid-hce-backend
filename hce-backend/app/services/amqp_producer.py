"""
Productor de eventos AMQP (RabbitMQ) para el módulo HCE.
Reemplaza al kafka_producer. Misma interfaz, diferente broker.

Topología:
  Exchange: healthgrid.events  (topic)
  Routing keys = nombres de los topics Kafka anteriores (migración sin fricción)
"""

import json
import logging
from typing import Optional

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Routing keys publicados por HCE ─────────────────────────────
RK_RECETA_CREADA = "clinica.farmacia.receta_creada"
RK_ORDEN_CREADA = "clinica.estudios.orden_creada"
RK_EPISODIO_CERRADO = "clinica.hce.episodio_cerrado"
RK_PATOLOGIA_CRITICA = "clinica.hce.patologia_critica_detectada"


class AMQPProducer:
    """
    Publicador de eventos async sobre RabbitMQ.
    Cae en modo log-only si RabbitMQ no está disponible.
    """

    def __init__(self):
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def start(self):
        try:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                settings.AMQP_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            logger.info("AMQP producer conectado a %s (exchange: %s)", settings.RABBITMQ_URL, settings.AMQP_EXCHANGE)
        except Exception as e:
            logger.warning("AMQP producer no disponible (%s). Los eventos se loguearan localmente.", e)
            self._connection = None
            self._channel = None
            self._exchange = None

    async def stop(self):
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def publish(self, routing_key: str, message: dict, correlation_id: Optional[str] = None):
        """Publicar mensaje al exchange con el routing key dado."""
        if self._exchange:
            body = json.dumps(message, ensure_ascii=False).encode("utf-8")
            amqp_msg = aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=correlation_id,
            )
            await self._exchange.publish(amqp_msg, routing_key=routing_key)
            logger.info("AMQP evento publicado [%s]: %s", routing_key, message)
        else:
            logger.info("[LOCAL] Evento que se publicaria en AMQP [%s]: %s", routing_key, message)


# Singleton — se importa desde los servicios de negocio
amqp_producer = AMQPProducer()
