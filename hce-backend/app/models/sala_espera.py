"""Modelo: Sala de Espera — Registro de pacientes esperando atención."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from common.enums.enums_sala_espera import EstadoSalaEspera


class SalaEspera(Base):
    __tablename__ = "sala_espera"

    id_espera: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(Integer, ForeignKey("pacientes.id_paciente"), index=True, nullable=False)
    id_episodio: Mapped[int | None] = mapped_column(Integer, ForeignKey("episodios.id_episodio"), index=True, nullable=True)
    id_medico: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_sede: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    id_turno_m2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_llegada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_turno: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    prioridad: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estado: Mapped[EstadoSalaEspera] = mapped_column(
        Enum(EstadoSalaEspera, name="estado_sala_espera", values_callable=lambda x: [e.value for e in x]),
        default=EstadoSalaEspera.ESPERANDO,
        nullable=False,
    )
    consultorio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motivo: Mapped[str | None] = mapped_column(String(500), default="-", server_default="-", nullable=True)

    # ─── Relaciones ───────────────────────────────────────────────
    paciente = relationship("Paciente", back_populates="sala_espera_registros", lazy="selectin")
    episodio = relationship("Episodio")
