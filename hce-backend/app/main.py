"""
Punto de entrada de la aplicación FastAPI.
Configura routers, lifespan y middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.kafka.consumer import start_kafka_consumer
from app.services.kafka_producer import kafka_producer
import asyncio
from app.routers import (
    alertas,
    antecedentes,
    core_integration,
    episodes,
    ficha_medica,
    health,
    historial,
    insurance,
    internacion,
    ordenes,
    recetas,
    resultados,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación.
    Aquí se podrían inicializar conexiones a Kafka, caches, etc.
    """
    # ── Startup ──
    print("🏥 HCE Module starting up...")
    await kafka_producer.start()
    asyncio.create_task(start_kafka_consumer())
    yield
    # ── Shutdown ──
    print("🥞 HCE Module shutting down...")
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
app.include_router(health.router, prefix=API_PREFIX, tags=["Integración M10 (Core)"])
app.include_router(core_integration.router, prefix=API_PREFIX, tags=["Integración M10 (Core)"])
app.include_router(recetas.router, prefix=API_PREFIX, tags=["Integración M3 (Farmacia)"])
app.include_router(ordenes.router, prefix=API_PREFIX, tags=["Integración M4/M5 (Estudios)"])
app.include_router(resultados.router, prefix=API_PREFIX, tags=["Integración M4/M5 (Estudios)"])
app.include_router(internacion.router, prefix=API_PREFIX, tags=["Integración M6 (Camas)"])
app.include_router(insurance.router, prefix=API_PREFIX, tags=["Integración M7 (Facturación)"])
app.include_router(historial.router, prefix=API_PREFIX, tags=["Integración M8 (Portal del Paciente)"])

