# Tareas de Integración para el Backend de HCE: Contadores de Episodios

Este documento detalla las modificaciones necesarias en el backend de HCE para agregar contadores agregados al endpoint de listado de episodios de un paciente. Esto permitirá al frontend mostrar la cantidad de Evoluciones, Recetas y Órdenes de cada episodio clínico en su primera vista sin sobrecargar la red.

---

## 1. Modificación de Esquema: `app/schemas/episodio.py`

En la definición de la clase `EpisodioResumen` (que representa el resumen de un episodio en la lista), añade tres nuevos campos enteros opcionales con un valor predeterminado de `0`.

### Cambios propuestos:

```python
class EpisodioResumen(BaseModel):
    """Resumen de un episodio para listados."""

    id_episodio: int = Field(..., examples=[700])
    tipo: TipoEpisodio = Field(..., examples=["internacion"])
    estado: EstadoEpisodio = Field(..., examples=["closed"])
    id_sede: int = Field(..., examples=[3])
    fecha_apertura: datetime = Field(..., examples=["2025-03-10T09:00:00Z"])
    fecha_cierre: Optional[datetime] = Field(None, examples=["2025-03-15T11:00:00Z"])
    id_medico_responsable: int = Field(..., examples=[42])
    
    # NUEVOS CONTADORES AGREGADOS
    cant_evoluciones: int = Field(default=0, description="Cantidad de evoluciones clínicas en este episodio.")
    cant_recetas: int = Field(default=0, description="Cantidad de recetas digitales emitidas en este episodio.")
    cant_estudios: int = Field(default=0, description="Cantidad de pedidos de estudios médicos solicitados en este episodio.")

    model_config = {"from_attributes": True}
```

---

## 2. Modificación de Router: `app/routers/episodes.py`

En el endpoint `GET /patients/{id_paciente}/episodes` (dentro de la función controladora `listar_episodios`), actualiza la inicialización de cada objeto `EpisodioResumen` para calcular los contadores dinámicamente basándote en las relaciones SQLAlchemy del modelo `Episodio` (`ep.evoluciones` y `ep.actos_medicos`).

*Nota: Como estas relaciones están configuradas con `lazy="selectin"` en los modelos, la carga en memoria ya se realiza de forma automática por SQLAlchemy, por lo que estas llamadas al tamaño de las listas son extremadamente veloces y no ejecutan consultas adicionales.*

### Cambios propuestos en la función `listar_episodios`:

```python
@router.get(
    "/patients/{id_paciente}/episodes",
    response_model=EpisodioListResponse,
    tags=["Atención Clínica — Episodios"],
    summary="Listar episodios médicos de un paciente",
    # ...
)
async def listar_episodios(
    id_paciente: int,
    db: DbSession,
    _user=Depends(require_permission("hce:episodes:read")),
    estado: Optional[str] = None,
    desde_fecha: Optional[date] = None,
    hasta_fecha: Optional[date] = None,
):
    try:
        episodios = await episodio_service.get_episodios_paciente(
            db, id_paciente, estado=estado, desde_fecha=desde_fecha, hasta_fecha=hasta_fecha
        )
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": str(e)},
        )

    return EpisodioListResponse(
        id_paciente=id_paciente,
        total=len(episodios),
        episodios=[
            EpisodioResumen(
                id_episodio=ep.id_episodio,
                tipo=ep.tipo,
                estado=ep.estado,
                id_sede=ep.id_sede,
                fecha_apertura=ep.fecha_apertura,
                fecha_cierre=ep.fecha_cierre,
                id_medico_responsable=ep.id_medico_responsable,
                # NUEVOS CONTADORES CALCULADOS
                cant_evoluciones=len(ep.evoluciones) if ep.evoluciones else 0,
                cant_recetas=sum(len(ev.recetas) for ev in ep.evoluciones if ev.recetas) if ep.evoluciones else 0,
                cant_estudios=len([a for a in ep.actos_medicos if a.tipo.value in ["estudio-laboratorio", "estudio-imagen"]]) if ep.actos_medicos else 0,
            )
            for ep in episodios
        ],
    )
```

---

## 3. Verificación de la API

Tras la modificación, la respuesta JSON esperada de `GET /patients/{id_paciente}/episodes` debería lucir similar a esto:

```json
{
  "id_paciente": 3001,
  "total": 1,
  "episodios": [
    {
      "id_episodio": 2,
      "tipo": "consulta-externa",
      "estado": "open",
      "id_sede": 3,
      "fecha_apertura": "2026-06-22T16:45:23.369040Z",
      "fecha_cierre": null,
      "id_medico_responsable": 42,
      "cant_evoluciones": 3,
      "cant_recetas": 2,
      "cant_estudios": 1
    }
  ]
}
```
