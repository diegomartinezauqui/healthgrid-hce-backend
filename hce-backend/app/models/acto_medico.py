"""Modelo: Acto Médico — prestación realizada dentro de un episodio."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ActoMedico(Base):
    __tablename__ = "actos_medicos"

    id_acto_medico: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_episodio: Mapped[int] = mapped_column(Integer, ForeignKey("episodios.id_episodio"), index=True)
    codigo_nomenclador: Mapped[str | None] = mapped_column(String(20), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tipo: Mapped[str] = mapped_column(
        Enum(
            "consulta",
            "estudio-laboratorio",
            "estudio-imagen",
            "procedimiento",
            "cirugia",
            "medicacion",
            "descartable",
            name="tipo_acto_medico",
        ),
    )
    id_profesional: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_realizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    episodio = relationship("Episodio", back_populates="actos_medicos")
