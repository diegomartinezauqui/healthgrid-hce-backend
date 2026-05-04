"""Modelo: Evolución médica — notas de consulta por profesionales de salud."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Evolucion(Base):
    __tablename__ = "evoluciones"

    id_evolucion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_episodio: Mapped[int] = mapped_column(Integer, ForeignKey("episodios.id_episodio"), index=True)
    id_profesional: Mapped[int] = mapped_column(Integer)
    contenido: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ─── Relaciones ───────────────────────────────────────────────
    recetas = relationship("Receta", back_populates="evolucion", lazy="selectin")
