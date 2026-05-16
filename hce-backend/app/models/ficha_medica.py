"""Modelo: Ficha Médica — datos clínicos permanentes del paciente."""

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FichaMedica(Base):
    __tablename__ = "fichas_medicas"

    # PK y FK lógica al M10 (Core) — el id_paciente ES la clave primaria
    id_paciente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pacientes.id_paciente"),
        primary_key=True,
    )

    grupo_sanguineo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    peso_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    altura_cm: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    observaciones_generales: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="ficha_medica")
