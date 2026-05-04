"""Modelo: Receta electrónica."""

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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
        Enum("Activa", "Suspendida", "Dispensada", name="estado_receta"),
        default="Activa",
    )

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="recetas")
    evolucion = relationship("Evolucion", back_populates="recetas")
