"""Modelo: Orden médica de estudio."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_orden import TipoEstudio, PrioridadOrden, SubtipoEstudio


class Orden(Base):
    __tablename__ = "ordenes"

    id_orden: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    id_episodio: Mapped[int | None] = mapped_column(Integer, ForeignKey("episodios.id_episodio"), index=True, nullable=True)
    id_evolucion: Mapped[int | None] = mapped_column(Integer, ForeignKey("evoluciones.id_evolucion"), index=True, nullable=True)
    tipo_estudio: Mapped[str] = mapped_column(
        Enum(TipoEstudio, name="tipo_estudio", values_callable=lambda x: [e.value for e in x])
    )
    descripcion_pedido: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prioridad: Mapped[str] = mapped_column(
        Enum(PrioridadOrden, name="prioridad_orden", values_callable=lambda x: [e.value for e in x]),
        default=PrioridadOrden.NORMAL
    )
    estado: Mapped[str] = mapped_column(String(50), default="Pendiente")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    id_medico_solicitante: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subtipo: Mapped[SubtipoEstudio | None] = mapped_column(
        Enum(SubtipoEstudio, name="subtipo_estudio_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    estudio_ids: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True
    )

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="ordenes")
    episodio = relationship("Episodio", foreign_keys=[id_episodio])
    evolucion = relationship("Evolucion", foreign_keys=[id_evolucion])
    resultados_laboratorio = relationship("ResultadoLaboratorio", back_populates="orden", cascade="all, delete-orphan")
    resultados_imagenes = relationship("ResultadoImagen", back_populates="orden", cascade="all, delete-orphan")
