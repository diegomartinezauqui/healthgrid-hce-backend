"""Modelo: Resultados de laboratorio e imágenes diagnósticas."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_orden import SubtipoEstudio


class ResultadoLaboratorio(Base):
    __tablename__ = "resultados_laboratorio"

    id_resultado_laboratorio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_orden: Mapped[int | None] = mapped_column(Integer, ForeignKey("ordenes.id_orden"), nullable=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    id_profesional_firmante: Mapped[str] = mapped_column(String(200))
    fecha_resultado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    informe_resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_externo_estudio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    analitos: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    resumen_analitos: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="resultados_laboratorio")
    orden = relationship("Orden", back_populates="resultados_laboratorio")


class ResultadoImagen(Base):
    __tablename__ = "resultados_imagenes"

    id_resultado_imagen: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_orden: Mapped[int | None] = mapped_column(Integer, ForeignKey("ordenes.id_orden"), nullable=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    id_profesional_firmante: Mapped[str] = mapped_column(String(200))
    fecha_resultado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    informe_resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_externo_estudio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subtipo: Mapped[SubtipoEstudio | None] = mapped_column(
        Enum(SubtipoEstudio, name="subtipo_estudio_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    link_imagen: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url_detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="resultados_imagenes")
    orden = relationship("Orden", back_populates="resultados_imagenes")
