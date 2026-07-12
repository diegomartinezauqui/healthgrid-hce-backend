"""Modelo: Alerta farmacológica del paciente (para Smart Payload de recetas → M3)."""

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_alertas import TipoAlertaFarmacologica

# To-do: Unificar con alerta_clinica
class AlertaFarmacologica(Base):
    __tablename__ = "alertas_farmacologicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    tipo: Mapped[str] = mapped_column(
        Enum(TipoAlertaFarmacologica, name="tipo_alerta_farmacologica"),
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="alertas_farmacologicas")
