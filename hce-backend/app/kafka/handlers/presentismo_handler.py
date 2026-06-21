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

        from app.database import async_session
        from app.schemas.sala_espera import SalaEsperaCreate
        from app.services import sala_espera_service

        # Convertir id_profesional a int de forma segura (ej. de "MP-12345" o "42" a 12345 o 42)
        id_medico = 1
        try:
            numeric_part = "".join(c for c in evento.id_profesional if c.isdigit())
            if numeric_part:
                id_medico = int(numeric_part)
        except Exception:
            pass

        # Usar sede por defecto 1 si no se especifica
        id_sede = 1

        sala_create = SalaEsperaCreate(
            id_paciente=evento.id_paciente,
            id_medico=id_medico,
            id_sede=id_sede,
            id_turno_m2=evento.id_turno_m2,
            fecha_turno=evento.fecha_hora_llegada,
            prioridad=1,
        )

        async with async_session() as db:
            await sala_espera_service.ingresar_paciente(db, evento.id_paciente, sala_create)
            await db.commit()

        logger.info("✅ Paciente %s ingresado a la sala de espera de forma automática", evento.id_paciente)

    except Exception as e:
        logger.error("❌ Error procesando evento de presentismo: %s", e)

