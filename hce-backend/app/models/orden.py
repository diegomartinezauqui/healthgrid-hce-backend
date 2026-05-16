"""Modelo: Orden médica de estudio."""

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_orden import TipoEstudio, PrioridadOrden


class Orden(Base):
    __tablename__ = "ordenes"

    id_orden: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    tipo_estudio: Mapped[str] = mapped_column(Enum(TipoEstudio))
    descripcion_pedido: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prioridad: Mapped[str] = mapped_column(Enum(PrioridadOrden), default="Normal")
    estado: Mapped[str] = mapped_column(String(50), default="Pendiente")

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="ordenes")
