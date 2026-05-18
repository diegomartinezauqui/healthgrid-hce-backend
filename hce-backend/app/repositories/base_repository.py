"""
Repositorio base genérico — equivalente al JpaRepository<T, ID> de Spring Boot.

Uso:
    class MiRepo(BaseRepository[MiModel, MiUpdateSchema]):
        def __init__(self):
            super().__init__(MiModel, MiModel.id_campo_pk)
"""

from typing import Any, Generic, Sequence, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ─── Type variables ──────────────────────────────────────────────────────────
# ModelT: sin bound explícito porque SQLAlchemy 2.x usa DeclarativeBase
# y el sistema de tipos de Python no puede resolverlo bien en runtime.
ModelT = TypeVar("ModelT")                       # tipo del modelo SQLAlchemy
UpdateT = TypeVar("UpdateT", bound=BaseModel)    # tipo del schema de actualización


class BaseRepository(Generic[ModelT, UpdateT]):
    """
    CRUD genérico asíncrono para SQLAlchemy 2.x.

    Parámetros
    ----------
    model : Type[ModelT]
        Clase del modelo ORM (ej. FichaMedica, Episodio).
    pk_column : InstrumentedAttribute
        Columna que actúa como clave primaria (ej. FichaMedica.id_paciente).
        Necesario porque cada modelo tiene un nombre de PK distinto.
    """

    def __init__(self, model: Type[ModelT], pk_column: Any) -> None:
        self.model = model
        self._pk = pk_column

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get(self, db: AsyncSession, pk: Any) -> ModelT | None:
        """Buscar un registro por su clave primaria."""
        result = await db.execute(
            select(self.model).where(self._pk == pk)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """Listar todos los registros con paginación opcional."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def exists(self, db: AsyncSession, pk: Any) -> bool:
        """Verificar si existe un registro con esa clave primaria."""
        return await self.get(db, pk) is not None

    # ── Write ─────────────────────────────────────────────────────────────────

    async def save(self, db: AsyncSession, instance: ModelT) -> ModelT:
        """
        Persistir un objeto ya construido (INSERT o UPDATE).
        El commit lo cierra el dependency get_db.
        """
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def update(
        self,
        db: AsyncSession,
        instance: ModelT,
        data: UpdateT,
    ) -> ModelT:
        """
        Actualización parcial: solo pisa los campos presentes en el schema
        (exclude_unset=True, equivalente a @Patch / PATCH semántico).
        """
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(instance, field, value)
        await db.flush()
        await db.refresh(instance)
        return instance

    async def delete(self, db: AsyncSession, pk: Any) -> bool:
        """
        Eliminar por PK. Retorna True si existía, False si no.
        """
        instance = await self.get(db, pk)
        if instance is None:
            return False
        await db.delete(instance)
        await db.flush()
        return True
