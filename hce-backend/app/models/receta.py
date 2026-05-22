"""Modelo: Receta electrónica."""

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_receta import EstadoReceta


class Receta(Base):
    __tablename__ = "recetas"

    id_receta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    id_evolucion: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("evoluciones.id_evolucion"), nullable=True
    )
    medicamento: Mapped[str] = mapped_column(String(300))
    indicaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(
        Enum(EstadoReceta, name="estado_receta", values_callable=lambda x: [e.value for e in x]),
        default=EstadoReceta.ACTIVA,
    )

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="recetas")
    evolucion = relationship("Evolucion", back_populates="recetas")
