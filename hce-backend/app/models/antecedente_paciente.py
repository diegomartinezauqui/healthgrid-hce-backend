"""Modelo: Antecedente del paciente (quirúrgicos, familiares, patológicos, hábitos)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_antecedente import TipoAntecedente


class AntecedentePaciente(Base):
    __tablename__ = "antecedente_paciente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(
        Integer, ForeignKey("pacientes.id_paciente"), index=True, nullable=False
    )
    tipo: Mapped[TipoAntecedente] = mapped_column(
        Enum(TipoAntecedente, name="tipo_antecedente"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_suceso: Mapped[date | None] = mapped_column(Date, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    id_medico_registro: Mapped[int] = mapped_column(Integer, nullable=False)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="antecedentes")
