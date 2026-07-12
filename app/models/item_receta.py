"""Modelo: Ítems de Receta electrónica (Medicamentos individuales)."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ItemReceta(Base):
    __tablename__ = "items_receta"

    id_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_receta: Mapped[int] = mapped_column(
        Integer, ForeignKey("recetas.id_receta", ondelete="CASCADE"), index=True
    )
    medicamento: Mapped[str] = mapped_column(String(300))
    indicaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, default=1)

    # ─── Relaciones ───────────────────────────────────────────────
    receta = relationship("Receta", back_populates="items")
