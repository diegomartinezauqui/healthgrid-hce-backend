"""Modelo: Solicitud de cama (internación o pase) gestionada con M6 (Camas).

Persiste la solicitud y su estado (pendiente/aceptada/rechazada/cancelada).
Cuando M6 la acepta, se registra la cama asignada y se crea el movimiento de
internación correspondiente. Cubre tanto la internación inicial (tipo=internacion)
como los pases de cama posteriores (tipo=pase).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SolicitudCama(Base):
    __tablename__ = "solicitudes_cama"

    id_solicitud: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_paciente: Mapped[int] = mapped_column(
        Integer, ForeignKey("pacientes.id_paciente"), index=True
    )
    id_episodio: Mapped[int] = mapped_column(
        Integer, ForeignKey("episodios.id_episodio"), index=True
    )
    # 'internacion' | 'pase'
    tipo: Mapped[str] = mapped_column(String(20), default="internacion")
    # 'Baja' | 'Media' | 'Alta'
    prioridad: Mapped[str] = mapped_column(String(20), default="Media")
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'pendiente' | 'aceptada' | 'rechazada' | 'cancelada'
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)
    # Datos que devuelve M6 al aceptar
    cama: Mapped[str | None] = mapped_column(String(50), nullable=True)
    habitacion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_solicitud: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
