"""
Punto de entrada de la aplicación FastAPI.
Configura routers, lifespan y middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import settings
from app.dependencies import verify_gateway_api_key
from app.kafka.consumer import start_kafka_consumer
from app.services.kafka_producer import kafka_producer
import asyncio
from app.routers import (
    alertas,
    antecedentes,
    core_integration,
    episodes,
    evoluciones,
    ficha_medica,
    health,
    historial,
    insurance,
    internacion,
    nomenclador,
    ordenes,
    pacientes,
    recetas,
    resultados,
    sala_espera,
    solicitudes_cama,
    webhooks,
)


import logging

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación.
    Aquí se podrían inicializar conexiones a Kafka, caches, etc.
    """
    # ── Startup ──
    logger.warning("HCE Module starting up...")
    consumer_task = None
    if settings.ENABLE_KAFKA:
        await kafka_producer.start()
        consumer_task = asyncio.create_task(start_kafka_consumer())
    else:
        logger.warning("[AVISO] Kafka esta deshabilitado en configuracion. Los eventos se loguearan localmente.")

    # Bus de eventos del Core (modelo real: RabbitMQ + POST /events/log).
    if settings.ENABLE_CORE_BUS:
        from app.integrations.rabbit_consumer import start_core_bus_consumer
        from app.services.core_subscription import registrar_suscripciones_core
        asyncio.create_task(start_core_bus_consumer())
        asyncio.create_task(registrar_suscripciones_core())

    yield
    # ── Shutdown ──
    logger.warning("HCE Module shutting down...")
    if consumer_task is not None and not consumer_task.done():
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    await kafka_producer.stop()


app = FastAPI(
    title="API Módulo 1 - Historia Clínica Electrónica (HCE)",
    description=(
        "Repositorio central de datos médicos del sistema Health Grid. "
        "Gestiona consultas, diagnósticos, tratamientos y fichas médicas."
    ),
    version="1.0.0",
    dependencies=[Depends(verify_gateway_api_key)],
    lifespan=lifespan,
    root_path="",
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.warning("❌ [FastAPI 422] Error de validación en ruta %s %s: %s", request.method, request.url.path, exc.errors())
    try:
        body = await request.json()
        logger.warning("Payload JSON que causó 422: %s", body)
    except Exception:
        try:
            body = await request.body()
            logger.warning("Payload raw que causó 422: %s", body)
        except Exception:
            pass
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# ─── Configuración de CORS ──────────────────────────────────────
# Los orígenes se leen de la variable de entorno ALLOWED_ORIGINS (config.py).
# En desarrollo el default incluye localhost:3000/5173/5174.
# En producción, definir en .env: ALLOWED_ORIGINS=https://app.healthgrid.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registrar routers con prefijo base /api/v1 ──────────────────
API_PREFIX = "/api/v1"

# ─── Router de desarrollo (solo en APP_ENV != production) ─────
if not settings.is_production:
    from app.routers import dev
    app.include_router(dev.router, prefix=API_PREFIX, tags=["🔧 Desarrollo"])

app.include_router(ficha_medica.router, prefix=API_PREFIX, tags=["Ficha Médica (HCE)"])
app.include_router(antecedentes.router, prefix=API_PREFIX, tags=["Ficha Médica — Antecedentes"])
app.include_router(alertas.router, prefix=API_PREFIX, tags=["Ficha Médica — Alertas Clínicas"])
app.include_router(episodes.router, prefix=API_PREFIX)
app.include_router(evoluciones.router, prefix=API_PREFIX)
app.include_router(pacientes.router, prefix=API_PREFIX, tags=["Ficha Médica (HCE)"])
app.include_router(recetas.router, prefix=API_PREFIX, tags=["Atención Clínica — Recetas"])
app.include_router(sala_espera.router, prefix=API_PREFIX, tags=["Atención Clínica — Sala de Espera"])
app.include_router(health.router, prefix=API_PREFIX, tags=["Integración M10 (Core)"])
app.include_router(core_integration.router, prefix=API_PREFIX, tags=["Integración M10 (Core)"])
app.include_router(ordenes.router, prefix=API_PREFIX, tags=["Atención Clínica — Órdenes Médicas"])
app.include_router(resultados.router, prefix=API_PREFIX, tags=["Atención Clínica — Órdenes Médicas"])
app.include_router(internacion.router, prefix=API_PREFIX, tags=["Integración M6 (Camas)"])
app.include_router(solicitudes_cama.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(insurance.router, prefix=API_PREFIX, tags=["Integración M7 (Facturación)"])
app.include_router(nomenclador.router, prefix=API_PREFIX)
app.include_router(historial.router, prefix=API_PREFIX, tags=["Integración M8 (Portal del Paciente)"])


# ─── Endpoint raíz ───────────────────────────────────────────────
_BANNER = """
██╗  ██╗███████╗ █████╗ ██╗  ████████╗██╗  ██╗ ██████╗ ██████╗ ██╗██████╗
██║  ██║██╔════╝██╔══██╗██║  ╚══██╔══╝██║  ██║██╔════╝ ██╔══██╗██║██╔══██╗
███████║█████╗  ███████║██║     ██║   ███████║██║  ███╗██████╔╝██║██║  ██║
██╔══██║██╔══╝  ██╔══██║██║     ██║   ██╔══██║██║   ██║██╔══██╗██║██║  ██║
██║  ██║███████╗██║  ██║███████╗██║   ██║  ██║╚██████╔╝██║  ██║██║██████╔╝
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝

  ╔══════════════════════════════════════════════════════════════╗
  ║        BACKEND CORRIENDO  —  MÓDULO 1 (HCE)  ✅             ║
  ║        Historia Clínica Electrónica — Health Grid            ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  API Docs  →  /docs                                          ║
  ║  ReDoc     →  /redoc                                         ║
  ║  Health    →  /api/v1/health                                 ║
  ╚══════════════════════════════════════════════════════════════╝
"""


@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz — muestra banner de estado del módulo HCE."""
    body = _BANNER + f"  version : 1.0.0\n  entorno : {settings.APP_ENV}\n"
    return Response(content=body, media_type="text/plain; charset=utf-8")
