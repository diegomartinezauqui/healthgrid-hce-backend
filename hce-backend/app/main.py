"""
Punto de entrada de la aplicación FastAPI.
Configura routers, lifespan y middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import (
    alertas,
    core_integration,
    episodes,
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
    yield
    # ── Shutdown ──
    print("🏥 HCE Module shutting down...")


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

app.include_router(health.router, prefix=API_PREFIX, tags=["Integración M10 (Core)"])
app.include_router(recetas.router, prefix=API_PREFIX, tags=["Integración M3 (Farmacia)"])
app.include_router(ordenes.router, prefix=API_PREFIX, tags=["Integración M4/M5 (Estudios)"])
app.include_router(resultados.router, prefix=API_PREFIX, tags=["Integración M4/M5 (Estudios)"])
app.include_router(internacion.router, prefix=API_PREFIX, tags=["Integración M6 (Camas)"])
app.include_router(episodes.router, prefix=API_PREFIX, tags=["Integración M7 (Facturación)"])
app.include_router(insurance.router, prefix=API_PREFIX, tags=["Integración M7 (Facturación)"])
app.include_router(historial.router, prefix=API_PREFIX, tags=["Integración M8 (Portal del Paciente)"])
app.include_router(alertas.router, prefix=API_PREFIX, tags=["Integración M9 (Monitoreo)"])
app.include_router(core_integration.router, prefix=API_PREFIX, tags=["Integración M10 (Core)"])
