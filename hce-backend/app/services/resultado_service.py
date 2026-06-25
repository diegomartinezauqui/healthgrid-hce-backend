"""Servicio de resultados de estudios — lógica para M4/M5 → HCE."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resultado import ResultadoLaboratorio, ResultadoImagen
from app.models.orden import Orden
from app.schemas.resultado import ResultadoEstudioRequest, ResultadoLaboratorioWebhook, ResultadoEstudioResumen

logger = logging.getLogger(__name__)


async def registrar_resultado(
    db: AsyncSession,
    data: ResultadoEstudioRequest,
) -> ResultadoImagen:
    """Registrar un resultado de estudio de Imagen en la HCE."""
    resultado = ResultadoImagen(
        id_orden=data.id_orden,
        id_paciente=data.id_paciente,
        id_profesional_firmante=data.id_profesional_firmante,
        fecha_resultado=data.fecha_resultado,
        titulo=data.informe_resumen.split(":")[0] if data.informe_resumen else "Resultado de Imagen",
        informe_resumen=data.informe_resumen,
        id_externo_estudio=data.id_externo_estudio,
        subtipo=data.subtipo,
        link_imagen=data.link_imagen,
        url_detalle=data.url_detalle,
    )
    db.add(resultado)
    await db.flush()

    # Actualizar estado de la orden asociada si existe
    if data.id_orden:
        res_orden = await db.execute(select(Orden).where(Orden.id_orden == data.id_orden))
        orden = res_orden.scalar_one_or_none()
        if orden:
            orden.estado = "Finalizado"
            logger.info("✅ Orden %s marcada como Finalizada tras recibir resultado de Imagen.", orden.id_orden)

    await db.commit()
    return resultado


async def registrar_resultado_laboratorio(
    db: AsyncSession,
    data: ResultadoLaboratorioWebhook,
) -> ResultadoLaboratorio:
    """
    Registrar el webhook de resultados del Módulo 4 (Laboratorio) en la HCE.
    Mapea el payload anidado y almacena los analitos en una estructura JSONB.
    """
    # Mapear el resumen y la lista de analitos a diccionarios para el almacenamiento JSONB
    analitos_dict_list = [analito.model_dump(mode="json") for analito in data.analitos]
    resumen_dict = data.resumen.model_dump(mode="json")

    resultado = ResultadoLaboratorio(
        id_orden=data.orden.id_orden_hce,
        id_paciente=data.paciente.id,
        id_profesional_firmante=data.profesional_firmante,
        fecha_resultado=data.fecha_ocurrencia,
        informe_resumen=data.orden.descripcion or "Resultado de Laboratorio Listo",
        id_externo_estudio=str(data.orden.id_laboratorio),
        analitos=analitos_dict_list,
        resumen_analitos=resumen_dict,
    )
    db.add(resultado)
    await db.flush()

    # Actualizar estado de la orden asociada si existe
    id_orden = data.orden.id_orden_hce
    if id_orden:
        res_orden = await db.execute(select(Orden).where(Orden.id_orden == id_orden))
        orden = res_orden.scalar_one_or_none()
        if orden:
            orden.estado = "Finalizado"
            logger.info("✅ Orden %s marcada como Finalizada tras recibir webhook de Laboratorio.", orden.id_orden)

    await db.commit()
    return resultado


async def get_resultados_paciente(
    db: AsyncSession, id_paciente: int
) -> list[ResultadoEstudioResumen]:
    """Obtener todos los resultados de un paciente (para M8 Portal) unificados."""
    # Query lab results
    q_lab = await db.execute(
        select(ResultadoLaboratorio).where(ResultadoLaboratorio.id_paciente == id_paciente)
    )
    labs = q_lab.scalars().all()

    # Query image results
    q_img = await db.execute(
        select(ResultadoImagen).where(ResultadoImagen.id_paciente == id_paciente)
    )
    imgs = q_img.scalars().all()

    unificados = []
    for l in labs:
        unificados.append(
            ResultadoEstudioResumen(
                id_resultado=l.id_resultado_laboratorio,
                id_orden=l.id_orden,
                tipo_estudio="Laboratorio",
                fecha_resultado=l.fecha_resultado,
                titulo="Resultado de Análisis de Laboratorio",
                resumen=l.informe_resumen,
                profesional_firmante=l.id_profesional_firmante,
                subtipo=None,
                link_imagen=None,
                url_detalle=None,
                analitos=l.analitos,
                resumen_analitos=l.resumen_analitos,
            )
        )

    for i in imgs:
        unificados.append(
            ResultadoEstudioResumen(
                id_resultado=i.id_resultado_imagen,
                id_orden=i.id_orden,
                tipo_estudio="Imagen",
                fecha_resultado=i.fecha_resultado,
                titulo=i.titulo or "Resultado de Diagnóstico por Imagen",
                resumen=i.informe_resumen,
                profesional_firmante=i.id_profesional_firmante,
                subtipo=i.subtipo,
                link_imagen=i.link_imagen,
                url_detalle=i.url_detalle,
                analitos=None,
                resumen_analitos=None,
            )
        )

    # Ordenar por fecha desc
    unificados.sort(key=lambda x: x.fecha_resultado, reverse=True)
    return unificados
