"""Modelo: Episodio médico (consulta, internación, guardia, cirugía)."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

from common.enums.enums_episodio import EstadoEpisodio, TipoActoMedico, TipoEpisodio


class Episodio(Base):
    __tablename__ = "episodios"

    id_episodio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    tipo: Mapped[TipoEpisodio] = mapped_column(
        Enum(TipoEpisodio, name="tipo_episodio"),
    )
    estado: Mapped[EstadoEpisodio] = mapped_column(
        Enum(EstadoEpisodio, name="estado_episodio"),
        default=EstadoEpisodio.OPEN,
    )
    id_sede: Mapped[int] = mapped_column(Integer)
    id_medico_responsable: Mapped[int] = mapped_column(Integer)
    diagnostico_principal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_apertura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="episodios")
    actos_medicos = relationship("ActoMedico", back_populates="episodio", lazy="selectin")
    movimientos = relationship("MovimientoInternacion", back_populates="episodio", lazy="selectin")
