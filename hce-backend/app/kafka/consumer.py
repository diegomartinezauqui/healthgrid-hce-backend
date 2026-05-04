"""
Consumidor Kafka del módulo HCE.
Consume eventos de otros módulos (ej: presentismo de M2).
"""

import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

TOPIC_PRESENTISMO = "clinica.turnos.presentismo"


async def start_kafka_consumer():
    """Iniciar el consumer loop de Kafka."""
    try:
        from aiokafka import AIOKafkaConsumer

        consumer = AIOKafkaConsumer(
            TOPIC_PRESENTISMO,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="hce-consumer-group",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        await consumer.start()
        logger.info("✅ Kafka consumer escuchando en: %s", TOPIC_PRESENTISMO)

        try:
            async for msg in consumer:
                logger.info("📥 Mensaje recibido en %s: %s", msg.topic, msg.value)
                if msg.topic == TOPIC_PRESENTISMO:
                    from app.kafka.handlers.presentismo_handler import handle_presentismo
                    await handle_presentismo(msg.value)
        finally:
            await consumer.stop()

    except Exception as e:
        logger.warning("⚠️ Kafka consumer no disponible: %s", e)
