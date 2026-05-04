"""Modelo: Cobertura médica del paciente (obra social / prepaga)."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CoberturaMedica(Base):
    __tablename__ = "coberturas_medicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    id_obra_social: Mapped[int] = mapped_column(Integer)
    nombre_obra_social: Mapped[str] = mapped_column(String(200))
    codigo_plan: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numero_afiliado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vigente_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="coberturas")
