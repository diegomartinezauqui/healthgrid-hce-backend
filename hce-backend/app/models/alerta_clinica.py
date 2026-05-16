"""Modelo: Alerta clínica del paciente (contraindicaciones, alergias para M4/M5/M9)."""

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_orden import TipoAlertaClinica

# To-do: Unificar con alerta_farmacologica
class AlertaClinica(Base):
    __tablename__ = "alertas_clinicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    tipo: Mapped[str] = mapped_column(
        Enum(TipoAlertaClinica, name="tipo_alerta_clinica"),
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="alertas_clinicas")
