"""
Configuración de la base de datos PostgreSQL con SQLAlchemy async.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ─── Engine asíncrono ─────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ─── Session factory ─────────────────────────────────────────────
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Base declarativa ────────────────────────────────────────────
class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass
