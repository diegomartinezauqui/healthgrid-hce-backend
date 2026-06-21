"""Servicio para gestionar el flujo de Sala de Espera."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sala_espera import SalaEspera
from app.models.episodio import Episodio
from app.repositories.paciente_repository import paciente_repo
from app.repositories.sala_espera_repository import sala_espera_repo
from app.schemas.sala_espera import SalaEsperaCreate
from common.enums.enums_sala_espera import EstadoSalaEspera
from common.enums.enums_episodio import EstadoEpisodio, TipoEpisodio
from app.schemas.episodio import EpisodioCreate
from app.services import episodio_service

logger = logging.getLogger(__name__)


async def get_sala_espera(
    db: AsyncSession,
    id_medico: Optional[int] = None,
    id_sede: Optional[int] = None,
    estado: Optional[str] = None,
    ordenar_por: Optional[str] = None,
) -> List[SalaEspera]:
    """Obtiene los registros de la sala de espera filtrados y ordenados."""
    return await sala_espera_repo.get_sala_filtrada(
        db, id_medico=id_medico, id_sede=id_sede, estado=estado, ordenar_por=ordenar_por
    )


async def ingresar_paciente(
    db: AsyncSession,
    id_paciente: int,
    data: SalaEsperaCreate,
) -> SalaEspera:
    """
    Ingresa un paciente a la sala de espera.
    Verifica que el paciente exista, busca o crea el episodio consulta-externa correspondiente y persiste el ingreso.
    """
    if not await paciente_repo.exists(db, id_paciente):
        raise LookupError(f"No existe el paciente con id {id_paciente}.")

    # Crear entrada de sala de espera sin asociar episodio aún (se creará diferido al atender)
    nueva_espera = SalaEspera(
        id_paciente=id_paciente,
        id_episodio=None,
        id_medico=data.id_medico,
        id_sede=data.id_sede,
        id_turno_m2=data.id_turno_m2,
        fecha_llegada=data.fecha_llegada or datetime.now(timezone.utc),
        fecha_turno=data.fecha_turno,
        prioridad=1,
        estado=EstadoSalaEspera.ESPERANDO,
        consultorio=None,
    )
    
    await sala_espera_repo.save(db, nueva_espera)
    return nueva_espera


async def llamar_paciente(
    db: AsyncSession,
    id_espera: int,
    consultorio: int,
) -> Optional[SalaEspera]:
    """Cambia el estado del registro a Llamado y asigna el consultorio correspondiente."""
    registro = await sala_espera_repo.get(db, id_espera)
    if not registro:
        return None

    registro.estado = EstadoSalaEspera.LLAMADO
    registro.consultorio = consultorio
    
    await db.flush()
    return registro


async def atender_paciente(
    db: AsyncSession,
    id_espera: int,
    id_episodio: Optional[int] = None,
) -> Optional[SalaEspera]:
    """
    Cambia el estado del registro a Atendido.
    Si se provee `id_episodio`, se vincula el episodio existente (validando pertenencia al paciente).
    Si se omite, se crea un nuevo episodio de consulta-externa automáticamente.
    """
    registro = await sala_espera_repo.get(db, id_espera)
    if not registro:
        return None

    if id_episodio is not None:
        from app.repositories.episodio_repository import episodio_repo
        episodio = await episodio_repo.get(db, id_episodio)
        if not episodio:
            raise ValueError(f"El episodio con id {id_episodio} no existe.")
        if episodio.id_paciente != registro.id_paciente:
            raise ValueError(
                f"El episodio con id {id_episodio} no pertenece al paciente {registro.id_paciente}."
            )
        registro.id_episodio = id_episodio
    else:
        # Abrir nuevo episodio de consulta-externa para esta consulta específica
        ep_create = EpisodioCreate(
            tipo=TipoEpisodio.CONSULTA_EXTERNA,
            diagnostico_principal="Atención iniciada desde sala de espera."
        )
        episodio = await episodio_service.abrir_episodio(
            db,
            id_paciente=registro.id_paciente,
            data=ep_create,
            id_medico=registro.id_medico,
            id_sede=registro.id_sede,
        )
        registro.id_episodio = episodio.id_episodio

    registro.estado = EstadoSalaEspera.ATENDIDO
    
    await db.flush()
    return registro


async def marcar_ausente(
    db: AsyncSession,
    id_espera: int,
) -> Optional[SalaEspera]:
    """Cambia el estado del registro a Ausente."""
    registro = await sala_espera_repo.get(db, id_espera)
    if not registro:
        return None

    registro.estado = EstadoSalaEspera.AUSENTE
    
    await db.flush()
    return registro
