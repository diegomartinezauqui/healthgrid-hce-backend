"""Modelo: Paciente — Ficha médica central."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Paciente(Base):
    __tablename__ = "pacientes"

    id_paciente: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    datos_personales: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ─── Relaciones ───────────────────────────────────────────────
    episodios = relationship("Episodio", back_populates="paciente", lazy="selectin")
    recetas = relationship("Receta", back_populates="paciente", lazy="selectin")
    ordenes = relationship("Orden", back_populates="paciente", lazy="selectin")
    resultados = relationship("Resultado", back_populates="paciente", lazy="selectin")
    alertas_clinicas = relationship("AlertaClinica", back_populates="paciente", lazy="selectin")
    alertas_farmacologicas = relationship("AlertaFarmacologica", back_populates="paciente", lazy="selectin")
    coberturas = relationship("CoberturaMedica", back_populates="paciente", lazy="selectin")
    ficha_medica = relationship("FichaMedica", back_populates="paciente", uselist=False, lazy="selectin")
