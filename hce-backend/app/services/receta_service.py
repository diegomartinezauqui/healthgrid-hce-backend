"""Servicio de recetas — lógica de negocio para M3 (Farmacia)."""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_clinica import AlertaClinicaPaciente
from app.models.receta import Receta
from app.repositories.alerta_repository import alerta_repo
from app.repositories.receta_repository import receta_repo
from app.schemas.receta import RecetaCreate


async def get_recetas(
    db: AsyncSession,
    estado: Optional[str] = None,
    id_paciente: Optional[int] = None,
    desde_fecha: Optional[date] = None,
) -> list[Receta]:
    """Obtener listado de recetas con filtros opcionales."""
    return await receta_repo.get_recetas_filtradas(
        db, estado=estado, id_paciente=id_paciente, desde_fecha=desde_fecha
    )


async def get_receta_by_id(db: AsyncSession, id_receta: int) -> Optional[Receta]:
    """Obtener una receta por su ID."""
    return await receta_repo.get_receta_detallada(db, id_receta)


async def get_alertas_farmacologicas_paciente(
    db: AsyncSession, id_paciente: int
) -> list[AlertaClinicaPaciente]:
    """Obtener alertas activas del paciente para Smart Payload en recetas."""
    return await alerta_repo.get_activas_by_paciente(db, id_paciente)


async def registrar_receta(
    db: AsyncSession, id_paciente: int, id_episodio: int, id_evolucion: int, data: RecetaCreate
) -> Receta:
    """Registra una nueva receta con sus medicamentos y notifica a M3 (Farmacia)."""
    
    # Determinar tipo_paciente buscando el episodio
    from app.repositories.episodio_repository import episodio_repo
    episodio = await episodio_repo.get(db, id_episodio)
    tipo_paciente = "Internado" if episodio and episodio.tipo == "internacion" else "Ambulatorio"

    # Crear cabecera
    nueva_receta = Receta(
        id_paciente=id_paciente,
        id_evolucion=id_evolucion,
    )
    db.add(nueva_receta)
    await db.flush()  # Para obtener el id_receta

    # Crear items
    from app.models.item_receta import ItemReceta
    
    for item_data in data.items:
        nuevo_item = ItemReceta(
            id_receta=nueva_receta.id_receta,
            medicamento=item_data.medicamento,
            indicaciones=item_data.indicaciones,
            cantidad=item_data.cantidad,
        )
        db.add(nuevo_item)
    
    await db.commit()
    await db.refresh(nueva_receta)

    return await receta_repo.get_receta_detallada(db, nueva_receta.id_receta)
