"""
Punto de entrada de la aplicación FastAPI.
Configura routers, lifespan y middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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
    ordenes,
    pacientes,
    recetas,
    resultados,
    sala_espera,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación.
    Aquí se podrían inicializar conexiones a Kafka, caches, etc.
    """
    # ── Startup ──
    print("🏥 HCE Module starting up...")
    consumer_task = None
    if settings.ENABLE_KAFKA:
        await kafka_producer.start()
        consumer_task = asyncio.create_task(start_kafka_consumer())
    else:
        print("⚠️ Kafka está deshabilitado en configuración. Los eventos se loguearán localmente.")

    yield
    # ── Shutdown ──
    print("🥞 HCE Module shutting down...")
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
    lifespan=lifespan,
    root_path="",
)

# ─── Configuración de CORS ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, reemplazar con el dominio del frontend
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
app.include_router(ordenes.router, prefix=API_PREFIX, tags=["Integración M4/M5 (Estudios)"])
app.include_router(resultados.router, prefix=API_PREFIX, tags=["Integración M4/M5 (Estudios)"])
app.include_router(internacion.router, prefix=API_PREFIX, tags=["Integración M6 (Camas)"])
app.include_router(insurance.router, prefix=API_PREFIX, tags=["Integración M7 (Facturación)"])
app.include_router(historial.router, prefix=API_PREFIX, tags=["Integración M8 (Portal del Paciente)"])

