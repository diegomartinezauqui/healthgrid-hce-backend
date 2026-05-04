"""Modelo: Movimiento de internación (ingreso/traslado de cama)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovimientoInternacion(Base):
    __tablename__ = "movimientos_internacion"

    id_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_episodio: Mapped[int] = mapped_column(Integer, ForeignKey("episodios.id_episodio"), index=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    sector: Mapped[str] = mapped_column(String(100))
    habitacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cama: Mapped[str] = mapped_column(String(50))
    fecha_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    medico_solicitante: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    episodio = relationship("Episodio", back_populates="movimientos")
