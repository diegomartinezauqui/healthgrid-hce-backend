"""Modelo: Alerta clínica del paciente (consideraciones de seguridad)."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_alertas import EstadoAlerta, SeveridadAlerta, TipoConsideracion


class AlertaClinicaPaciente(Base):
    __tablename__ = "alerta_clinica_paciente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(
        Integer, ForeignKey("pacientes.id_paciente"), index=True, nullable=False
    )
    tipo: Mapped[TipoConsideracion] = mapped_column(
        Enum(TipoConsideracion, name="tipo_consideracion"), nullable=False
    )
    severidad: Mapped[SeveridadAlerta] = mapped_column(
        Enum(SeveridadAlerta, name="severidad_alerta"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoAlerta] = mapped_column(
        Enum(EstadoAlerta, name="estado_alerta"),
        default=EstadoAlerta.ACTIVA,
        nullable=False,
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    id_medico_registro: Mapped[int] = mapped_column(Integer, nullable=False)

    # Campos de resolución — solo se completan al resolver la alerta
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    id_medico_resolucion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo_resolucion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="alertas")
