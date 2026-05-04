"""
Productor de eventos Kafka.
Publica mensajes a los tópicos configurados del módulo HCE.
"""

import json
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Tópicos Kafka de HCE ────────────────────────────────────────
TOPIC_RECETA_CREADA = "clinica.farmacia.receta_creada"
TOPIC_ORDEN_CREADA = "clinica.estudios.orden_creada"
TOPIC_EPISODIO_CERRADO = "clinica.hce.episodio_cerrado"
TOPIC_PATOLOGIA_CRITICA = "clinica.hce.patologia_critica_detectada"


class KafkaProducer:
    """
    Wrapper del productor Kafka.
    En desarrollo, solo loguea los mensajes. En producción, usa aiokafka.
    """

    def __init__(self):
        self._producer = None

    async def start(self):
        """Inicializar el productor Kafka."""
        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            logger.info("✅ Kafka producer conectado a %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            logger.warning(
                "⚠️ No se pudo conectar a Kafka (%s). Los eventos se loguearán localmente.",
                e,
            )
            self._producer = None

    async def stop(self):
        """Cerrar el productor Kafka."""
        if self._producer:
            await self._producer.stop()

    async def publish(self, topic: str, message: dict, key: Optional[str] = None):
        """Publicar un mensaje a un tópico Kafka."""
        if self._producer:
            key_bytes = key.encode("utf-8") if key else None
            await self._producer.send_and_wait(topic, message, key=key_bytes)
            logger.info("📤 Evento publicado en %s: %s", topic, message)
        else:
            # Fallback: loguear el evento cuando Kafka no está disponible
            logger.info(
                "📤 [LOCAL] Evento que se publicaría en %s: %s", topic, message
            )


# Instancia singleton del productor
kafka_producer = KafkaProducer()
