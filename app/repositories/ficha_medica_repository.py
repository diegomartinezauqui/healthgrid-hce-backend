"""Repositorio de FichaMedica — extiende BaseRepository con lógica específica."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha_medica import FichaMedica
from app.repositories.base_repository import BaseRepository
from app.schemas.ficha_medica import FichaMedicaCreate, FichaMedicaUpdate


class FichaMedicaRepository(BaseRepository[FichaMedica, FichaMedicaUpdate]):
    """
    Repositorio de FichaMedica.

    Hereda de BaseRepository:
      - get(db, pk)          → buscar por id_paciente
      - get_all(db)          → listar todos (uso interno/admin)
      - exists(db, pk)       → verificar existencia
      - save(db, instance)   → INSERT de objeto ya construido
      - update(db, obj, data)→ PATCH parcial
      - delete(db, pk)       → DELETE por PK

    Métodos específicos de este repositorio:
      - get_by_paciente      → alias semántico de get()
      - create               → construye el objeto y llama a save()
    """

    def __init__(self) -> None:
        # Le indicamos al base cuál es el modelo y cuál columna es la PK
        super().__init__(FichaMedica, FichaMedica.id_paciente)

    async def get_by_paciente(
        self,
        db: AsyncSession,
        id_paciente: int,
    ) -> FichaMedica | None:
        """Alias semántico: buscar ficha médica por id de paciente."""
        return await self.get(db, id_paciente)

    async def create(
        self,
        db: AsyncSession,
        id_paciente: int,
        data: FichaMedicaCreate,
    ) -> FichaMedica:
        """Construir la entidad con los datos del schema y persistirla."""
        ficha = FichaMedica(
            id_paciente=id_paciente,
            grupo_sanguineo=data.grupo_sanguineo,
            peso_kg=data.peso_kg,
            altura_cm=data.altura_cm,
            observaciones_generales=data.observaciones_generales,
        )
        return await self.save(db, ficha)


# Singleton listo para inyectar en los services
ficha_medica_repo = FichaMedicaRepository()
