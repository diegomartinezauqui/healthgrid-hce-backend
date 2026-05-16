"""Modelo: Resultado de estudio médico."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_orden import TipoEstudio


class Resultado(Base):
    __tablename__ = "resultados_estudios"

    id_resultado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True)
    tipo_estudio: Mapped[str] = mapped_column(
        Enum(TipoEstudio, name="tipo_estudio_resultado"),
    )
    id_profesional_firmante: Mapped[str] = mapped_column(String(200))
    fecha_resultado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    informe_resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_externo_estudio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    titulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    resumen: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="resultados")
