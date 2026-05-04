"""
Handler para el evento de presentismo (M2 Turnos → HCE).
Cuando un paciente se registra en recepción, HCE prepara la evolución médica.
"""

import logging

from app.schemas.kafka_events import EventoKafkaPresentismo

logger = logging.getLogger(__name__)


async def handle_presentismo(data: dict):
    """Procesar evento de presentismo recibido de M2."""
    try:
        evento = EventoKafkaPresentismo(**data)
        logger.info(
            "👤 Presentismo recibido — Paciente: %s, Profesional: %s, Turno M2: %s",
            evento.id_paciente,
            evento.id_profesional,
            evento.id_turno_m2,
        )
        # TODO: Crear/preparar la evolución médica correspondiente
        # - Buscar o crear episodio de consulta-externa
        # - Vincular con el profesional asignado
        # - Marcar como "en espera de atención"

    except Exception as e:
        logger.error("❌ Error procesando evento de presentismo: %s", e)
