# 🏥 HCE Backend — Módulo 1: Historia Clínica Electrónica

Backend API del módulo de Historia Clínica Electrónica del sistema **Health Grid**.

## Stack Tecnológico

- **Framework**: FastAPI (Python 3.11+)
- **Base de datos**: PostgreSQL 16 (async via asyncpg)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migraciones**: Alembic
- **Mensajería**: Apache Kafka (aiokafka)
- **Auth**: JWT validado localmente (emitido por Módulo 10 - Core)

## Quick Start

### 1. Clonar y preparar entorno

```bash
# Crear virtual environment
python -m venv venv
venv\Scripts\activate    # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
copy .env.example .env
```

### 2. Levantar PostgreSQL

```bash
docker compose up -d postgres
```

### 3. Ejecutar migraciones

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 4. Iniciar el servidor

```bash
uvicorn app.main:app --reload --port 8001
```

### 5. Ver documentación

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Estructura del proyecto

```
app/
├── auth/          # Validación JWT + permisos
├── models/        # Modelos SQLAlchemy (tablas)
├── schemas/       # Pydantic schemas (request/response)
├── routers/       # Endpoints por integración
├── services/      # Lógica de negocio
└── kafka/         # Consumidores de eventos
```

## Endpoints implementados

| Método | Path | Integración | Permiso |
|--------|------|------------|---------|
| GET | `/api/v1/hce/health` | M10 | Sin auth |
| GET | `/api/v1/recetas` | M3 | `hce:recetas:read` |
| GET | `/api/v1/recetas/{id}` | M3 | `hce:recetas:read` |
| GET | `/api/v1/ordenes` | M4/M5 | `hce:ordenes:read` |
| GET | `/api/v1/ordenes/{id}` | M4/M5 | `hce:ordenes:read` |
| POST | `/api/v1/resultados` | M4/M5 | `hce:resultados:write` |
| POST | `/api/v1/internacion/ingreso` | M6 | `hce:internacion:write` |
| GET | `/api/v1/patients/{id}/episodes` | M7 | `hce:episodes:read` |
| GET | `/api/v1/patients/{id}/episodes/{id}` | M7 | `hce:episodes:read` |
| GET | `/api/v1/patients/{id}/episodes/{id}/medical-acts` | M7 | `hce:medical-acts:read` |
| GET | `/api/v1/patients/{id}/insurance` | M7 | `hce:insurance:read` |
| GET | `/api/v1/pacientes/{id}/historial/recetas` | M8 | `hce:recetas:read` |
| GET | `/api/v1/pacientes/{id}/historial/resultados` | M8 | `hce:resultados:read` |
| GET | `/api/v1/pacientes/{id}/alertas` | M9 | `hce:contraindications:read` |
| POST | `/api/v1/hce/notify-permission-change` | M10 | `hce:write` |

## Eventos Kafka

### HCE Publica
- `clinica.farmacia.receta_creada` → M3
- `clinica.estudios.orden_creada` → M4/M5
- `clinica.hce.episodio_cerrado` → M6, M7
- `clinica.hce.patologia_critica_detectada` → M10

### HCE Consume
- `clinica.turnos.presentismo` ← M2
