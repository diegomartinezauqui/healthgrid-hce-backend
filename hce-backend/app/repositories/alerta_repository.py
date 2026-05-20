"""Repositorio de AlertaClinicaPaciente."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinicaPaciente
from app.repositories.base_repository import BaseRepository
from app.schemas.alerta import AlertaCreate, AlertaUpdate
from common.enums.enums_alertas import EstadoAlerta


class AlertaRepository(BaseRepository[AlertaClinicaPaciente, AlertaUpdate]):
    """
    Repositorio de AlertaClinicaPaciente.

    Hereda de BaseRepository:
      - get(db, pk)           → buscar por id
      - exists(db, pk)        → verificar existencia
      - save(db, instance)    → INSERT
      - update(db, obj, data) → PATCH parcial
      - delete(db, pk)        → DELETE

    Métodos específicos:
      - get_by_paciente       → todas las alertas de un paciente
      - get_activas_by_paciente → solo alertas Activa (para Smart Payload)
      - create                → construye la entidad y llama a save()
    """

    def __init__(self) -> None:
        super().__init__(AlertaClinicaPaciente, AlertaClinicaPaciente.id)

    async def get_by_paciente(
        self, db: AsyncSession, id_paciente: int
    ) -> list[AlertaClinicaPaciente]:
        """Todas las alertas de un paciente (Activas y Resueltas)."""
        result = await db.execute(
            select(AlertaClinicaPaciente).where(
                AlertaClinicaPaciente.id_paciente == id_paciente
            )
        )
        return list(result.scalars().all())

    async def get_activas_by_paciente(
        self, db: AsyncSession, id_paciente: int
    ) -> list[AlertaClinicaPaciente]:
        """Solo alertas Activas — para Smart Payload en órdenes y recetas."""
        result = await db.execute(
            select(AlertaClinicaPaciente).where(
                AlertaClinicaPaciente.id_paciente == id_paciente,
                AlertaClinicaPaciente.estado == EstadoAlerta.ACTIVA,
            )
        )
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, id_paciente: int, data: AlertaCreate, id_medico: int
    ) -> AlertaClinicaPaciente:
        """Construye la entidad con los datos del schema y la persiste."""
        alerta = AlertaClinicaPaciente(
            id_paciente=id_paciente,
            tipo=data.tipo,
            severidad=data.severidad,
            descripcion=data.descripcion,
            id_medico_registro=id_medico,
        )
        return await self.save(db, alerta)


# Singleton
alerta_repo = AlertaRepository()
