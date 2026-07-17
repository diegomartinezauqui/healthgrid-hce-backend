# Arquitectura — Módulo 1: Historia Clínica Electrónica (HCE)

> **Health Grid** · Desarrollo de Aplicaciones II · Ing. Joaquín Timerman
>
> Este documento describe la arquitectura interna del Módulo 1, sus contratos de integración con los demás módulos y los flujos de datos principales. Está pensado para ser compartido con el resto de los grupos y como insumo para el diagrama de arquitectura integrado final.

---

## Tabla de contenidos

1. [Responsabilidad del módulo](#1-responsabilidad-del-módulo)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Diagrama de arquitectura interna](#3-diagrama-de-arquitectura-interna)
4. [Diagrama de integración con otros módulos](#4-diagrama-de-integración-con-otros-módulos)
5. [Modelo de datos](#5-modelo-de-datos)
6. [API expuesta (contratos de entrada)](#6-api-expuesta-contratos-de-entrada)
7. [Llamadas salientes (contratos de salida)](#7-llamadas-salientes-contratos-de-salida)
8. [Integración asincrónica — Kafka](#8-integración-asincrónica--kafka)
9. [Autenticación y autorización](#9-autenticación-y-autorización)
10. [Flujos principales (diagramas de secuencia)](#10-flujos-principales-diagramas-de-secuencia)
11. [Cómo levantar el módulo localmente](#11-cómo-levantar-el-módulo-localmente)
12. [Variables de entorno](#12-variables-de-entorno)

---

## 1. Responsabilidad del módulo

El **Módulo 1 — HCE** es el **repositorio central de datos médicos** del sistema Health Grid. Actúa como fuente de verdad clínica para todos los demás módulos.

### Funciones principales

| Función | Descripción |
|---------|-------------|
| **Registro Clínico** | Creación y actualización de la ficha médica permanente del paciente (antecedentes, alergias, grupo sanguíneo, etc.) |
| **Evolución Médica** | Carga de notas de consulta (evoluciones) por parte de profesionales de salud en cada episodio |
| **Episodios de Atención** | Apertura y cierre de episodios médicos (guardia, consulta externa, internación) |
| **Órdenes de Estudio** | Emisión de órdenes de laboratorio (M4) e imágenes diagnósticas (M5) con smart payload de alertas clínicas |
| **Recetas Electrónicas** | Generación y gestión de recetas médicas para dispensación por farmacia (M3) |
| **Sala de Espera** | Gestión de la cola de atención desde el check-in del paciente hasta ser atendido |
| **Consulta Externa** | Exposición de contraindicaciones y alertas clínicas para que otros módulos validen antes de un estudio o medicación |
| **Notificación Crítica** | Emisión de eventos asincrónicos ante detección de patologías de notificación obligatoria |

---

## 2. Stack tecnológico

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Framework web | FastAPI | >= 0.115 |
| Servidor ASGI | Uvicorn | >= 0.30 |
| Base de datos | PostgreSQL | 16 |
| ORM | SQLAlchemy (async) | >= 2.0 |
| Driver DB | asyncpg | >= 0.29 |
| Migraciones | Alembic | >= 1.13 |
| Mensajería | Apache Kafka (aiokafka) | >= 0.10 |
| Cliente HTTP | httpx (async) | >= 0.27 |
| Autenticación | JWT (python-jose) | HS256 |
| Configuración | pydantic-settings | >= 2.2 |
| Lenguaje | Python | 3.11+ |

---

## 3. Diagrama de arquitectura interna

```mermaid
graph TB
    subgraph Cliente["Clientes externos"]
        BROWSER[Browser / Otros módulos]
    end

    subgraph HCE["Módulo 1 — HCE  (puerto 8000)"]
        direction TB

        subgraph TRANSPORT["Capa de transporte"]
            ROUTER[Routers FastAPI<br/>─────────────<br/>18 archivos de rutas<br/>/api/v1/...]
            KAFKA_C[Kafka Consumer<br/>clinica.turnos.presentismo]
        end

        subgraph LOGIC["Capa de lógica de negocio"]
            SERVICE[Services<br/>─────────────<br/>episodio · evolucion<br/>orden · receta · alerta<br/>sala_espera · internacion]
            KAFKA_P[Kafka Producer<br/>─────────────<br/>episodio_cerrado<br/>patologia_critica]
        end

        subgraph INTEGRATION["Capa de integración saliente"]
            M4_CLI[m4_client.py]
            M5_CLI[m5_client.py]
            M6_CLI[m6_client.py]
            CORE_CLI[core_client.py]
        end

        subgraph DATA["Capa de datos"]
            REPO[Repositories<br/>─────────────<br/>11 repositorios]
            DB[(PostgreSQL<br/>17 tablas)]
        end

        ROUTER --> SERVICE
        KAFKA_C --> SERVICE
        SERVICE --> REPO
        SERVICE --> KAFKA_P
        SERVICE --> M4_CLI
        SERVICE --> M5_CLI
        SERVICE --> M6_CLI
        SERVICE --> CORE_CLI
        REPO --> DB
    end

    BROWSER -->|HTTP + JWT Bearer| ROUTER
```

### Estructura de carpetas

```
hce-backend/
├── app/
│   ├── auth/           # Validación JWT + permisos por claim
│   ├── integrations/   # Clientes HTTP hacia M4, M5, M10
│   ├── kafka/          # Consumer (M2) + Producer
│   ├── models/         # Modelos SQLAlchemy (17 tablas)
│   ├── repositories/   # Acceso a datos (patrón Repository)
│   ├── routers/        # Endpoints agrupados por integración
│   ├── schemas/        # Pydantic DTOs (request/response)
│   ├── services/       # Lógica de negocio + clientes HTTP M6
│   ├── config.py       # Variables de entorno (pydantic-settings)
│   ├── database.py     # Engine async SQLAlchemy
│   ├── dependencies.py # Inyección de dependencias FastAPI
│   └── main.py         # Punto de entrada, registro de routers
├── alembic/            # Migraciones (14 revisiones)
├── common/enums/       # Enumeraciones compartibles entre módulos
├── tests/              # Suite de tests (pytest-asyncio)
└── docker-compose.yml  # PostgreSQL + Kafka (opcional)
```

---

## 4. Diagrama de integración con otros módulos

```mermaid
graph LR
    subgraph M1["M1 — HCE :8000"]
        WH_M2["POST /webhook/turnos/presentismo"]
        WH_M4["POST /webhook/laboratorio/resultado"]
        WH_M5["POST /webhook/imagenes/reporte"]
        WH_M6["POST /internacion/ingreso"]
        EP_ORDENES["GET /ordenes\nGET /ordenes/{id}"]
        EP_EPISODES["GET /patients/{id}/episodes\nGET /patients/{id}/episodes/{id}"]
        EP_ACTOS["GET /patients/{id}/episodes/{id}/medical-acts"]
        EP_INSURANCE["GET /patients/{id}/insurance"]
        EP_HISTORIAL["GET /pacientes/{id}/historial/recetas\nGET /pacientes/{id}/historial/resultados"]
        EP_HEALTH["GET /hce/health"]
        EP_CORE["POST /hce/notify-permission-change"]
    end

    M2["M2\nTurnos\n:8002"] -->|check-in paciente| WH_M2
    M4["M4\nLaboratorio\n:8004"] -->|resultado finalizado| WH_M4
    M4 -->|sync órdenes pendientes| EP_ORDENES
    M5["M5\nImágenes\nonrender.com"] -->|informe finalizado| WH_M5
    M5 -->|sync órdenes pendientes| EP_ORDENES
    M6["M6\nCamas\n:8006"] -->|ingreso a cama confirmado| WH_M6
    M7["M7\nFacturación"] -->|liquidación prestaciones| EP_EPISODES
    M7 -->|actos médicos| EP_ACTOS
    M7 -->|cobertura médica| EP_INSURANCE
    M8["M8\nPortal Paciente"] -->|historial Mi Salud| EP_HISTORIAL
    M10["M10\nCore\n:8010"] -->|health check| EP_HEALTH
    M10 -->|cambio de permisos| EP_CORE

    WH_M2 -.->|POST /v1/ordenes| M4
    WH_M2 -.->|POST /v1/webhook/orders| M5
    WH_M2 -.->|POST /M6/solicitudes-internacion| M6
    WH_M2 -.->|POST /events/subscriptions| M10

    style M1 fill:#1e293b,stroke:#6366f1,color:#e2e8f0
```

### Resumen de integraciones

| Módulo | Dirección | Tipo | Descripción |
|--------|-----------|------|-------------|
| M2 — Turnos | M2 → HCE | REST webhook | Check-in del paciente ingresa a sala de espera |
| M4 — Laboratorio | HCE → M4 | REST saliente | HCE notifica nueva orden de lab |
| M4 — Laboratorio | M4 → HCE | REST webhook | M4 entrega resultado finalizado |
| M4 — Laboratorio | M4 → HCE | REST (GET) | M4 sincroniza órdenes pendientes |
| M5 — Imágenes | HCE → M5 | REST saliente | HCE notifica nueva orden de imágenes |
| M5 — Imágenes | M5 → HCE | REST webhook | M5 entrega informe finalizado |
| M5 — Imágenes | M5 → HCE | REST (GET) | M5 sincroniza órdenes pendientes |
| M6 — Camas | HCE → M6 | REST saliente | HCE solicita asignación de cama |
| M6 — Camas | M6 → HCE | REST webhook | M6 notifica ingreso físico a cama |
| M7 — Facturación | M7 → HCE | REST (GET) | M7 obtiene episodios, actos y cobertura para liquidar |
| M8 — Portal | M8 → HCE | REST (GET) | M8 obtiene historial de recetas y resultados |
| M10 — Core | HCE → M10 | REST saliente | HCE se suscribe a eventos en startup |
| M10 — Core | M10 → HCE | REST | Health check y cambios de permisos |

---

## 5. Modelo de datos

### Diagrama entidad-relación (tablas principales)

```mermaid
erDiagram
    pacientes {
        int id_paciente PK
        jsonb datos_personales
        timestamp created_at
    }
    fichas_medicas {
        int id_ficha PK
        int id_paciente FK
        string grupo_sanguineo
        float peso_kg
        float altura_cm
        text observaciones_generales
    }
    antecedente_paciente {
        int id_antecedente PK
        int id_paciente FK
        string tipo
        string descripcion
        date fecha_registro
    }
    alerta_clinica_paciente {
        int id_alerta PK
        int id_paciente FK
        string tipo
        string severidad
        string descripcion
    }
    episodios {
        int id_episodio PK
        int id_paciente FK
        string tipo
        string estado
        int id_sede
        int id_medico_responsable
        string diagnostico_principal
        timestamp fecha_apertura
        timestamp fecha_cierre
    }
    evoluciones {
        int id_evolucion PK
        int id_episodio FK
        int id_medico
        text nota_clinica
        timestamp fecha_hora
    }
    actos_medicos {
        int id_acto_medico PK
        int id_episodio FK
        string codigo_nomenclador
        string descripcion
        string tipo
        int id_profesional
        timestamp fecha_realizacion
    }
    recetas {
        int id_receta PK
        int id_paciente FK
        int id_evolucion FK
        string medicamento
        string indicaciones
        string estado
    }
    items_receta {
        int id_item PK
        int id_receta FK
        string medicamento
        string cantidad
        string indicaciones
    }
    ordenes {
        int id_orden PK
        int id_paciente FK
        int id_episodio FK
        int id_evolucion FK
        string tipo_estudio
        string subtipo
        string descripcion_pedido
        string prioridad
        string estado
        jsonb estudio_ids
        int id_medico_solicitante
    }
    resultados_laboratorio {
        int id_resultado PK
        int id_orden FK
        int id_paciente FK
        string profesional_firmante
        timestamp fecha_resultado
        jsonb analitos
    }
    resultados_imagenes {
        int id_resultado PK
        int id_orden FK
        int id_paciente FK
        string informe_resumen
        string subtipo
        string link_imagen
        string url_detalle
    }
    coberturas_medicas {
        int id_cobertura PK
        int id_paciente FK
        string nombre_obra_social
        string numero_afiliado
        date vigente_desde
    }
    sala_espera {
        int id_espera PK
        int id_paciente FK
        int id_episodio FK
        string estado
        string tipo_atencion
        timestamp fecha_llegada
        int consultorio
    }
    solicitudes_cama {
        int id_solicitud PK
        int id_paciente FK
        int id_episodio FK
        string tipo
        string prioridad
        string sector
        string estado
        string cama
        string habitacion
    }
    movimientos_internacion {
        int id_movimiento PK
        int id_episodio FK
        string sector
        string habitacion
        string cama
        timestamp fecha_ingreso
    }

    pacientes ||--o| fichas_medicas : tiene
    pacientes ||--o{ antecedente_paciente : tiene
    pacientes ||--o{ alerta_clinica_paciente : tiene
    pacientes ||--o{ episodios : tiene
    pacientes ||--o{ recetas : tiene
    pacientes ||--o{ ordenes : tiene
    pacientes ||--o{ coberturas_medicas : tiene
    episodios ||--o{ evoluciones : contiene
    episodios ||--o{ actos_medicos : registra
    episodios ||--o{ solicitudes_cama : genera
    episodios ||--o{ movimientos_internacion : registra
    evoluciones ||--o{ recetas : genera
    evoluciones ||--o{ ordenes : genera
    recetas ||--o{ items_receta : tiene
    ordenes ||--o| resultados_laboratorio : tiene
    ordenes ||--o| resultados_imagenes : tiene
```

### Tablas completas

| Tabla | Descripción |
|-------|-------------|
| `pacientes` | Caché local de datos demográficos (origen: M10 Core) |
| `fichas_medicas` | Datos clínicos estáticos permanentes del paciente |
| `antecedente_paciente` | Antecedentes médicos (cirugías, patologías previas, etc.) |
| `alerta_clinica_paciente` | Alergias y alertas clínicas del paciente |
| `episodios` | Encuentros médicos (guardia, consulta, internación) |
| `evoluciones` | Notas clínicas redactadas por el profesional en cada consulta |
| `actos_medicos` | Prestaciones registradas en un episodio (para facturación) |
| `recetas` | Recetas electrónicas emitidas en evoluciones |
| `items_receta` | Medicamentos individuales de cada receta |
| `ordenes` | Órdenes de laboratorio e imágenes con smart payload de alertas |
| `resultados_laboratorio` | Resultados de análisis con analitos y rangos de referencia |
| `resultados_imagenes` | Informes de estudios de imágenes con link PACS |
| `coberturas_medicas` | Obra social / prepaga vigente del paciente |
| `sala_espera` | Cola de atención desde check-in hasta ser atendido |
| `solicitudes_cama` | Solicitudes de internación o pase de cama enviadas a M6 |
| `movimientos_internacion` | Historial de camas asignadas a un episodio de internación |
| `alembic_version` | Control de versión de migraciones |

---

## 6. API expuesta (contratos de entrada)

> **Base URL:** `http://localhost:8000/api/v1`
> **Autenticación:** `Authorization: Bearer <JWT>` (emitido por M10 Core, firmado con clave compartida HS256)

### Webhooks de integración (entrada de otros módulos)

| Método | Endpoint | Consume | Permiso requerido |
|--------|----------|---------|-------------------|
| `POST` | `/webhook/turnos/presentismo` | M2 | Sin permiso (webhook público) |
| `POST` | `/webhook/laboratorio/resultado` | M4 / M10 | `hce:resultados:write` |
| `POST` | `/webhook/imagenes/reporte` | M5 / M10 | `hce:resultados:write` |
| `POST` | `/internacion/ingreso` | M6 | `hce:internacion:write` |

### Órdenes médicas (M4 y M5 consultan)

| Método | Endpoint | Consume | Permiso requerido |
|--------|----------|---------|-------------------|
| `GET` | `/ordenes?tipo_estudio={lab\|imagen}&estado={Pendiente}` | M4, M5 | `hce:ordenes:read` |
| `GET` | `/ordenes/{id_orden}` | M4, M5 | `hce:ordenes:read` |
| `POST` | `/pacientes/{id}/ordenes/laboratorio` | Médicos / HCE interno | `hce:ordenes:write` |
| `POST` | `/pacientes/{id}/ordenes/imagenes` | Médicos / HCE interno | `hce:ordenes:write` |

> El `GET /ordenes/{id}` devuelve un **Smart Payload** que incluye las alertas clínicas del paciente para que M4/M5 puedan validar contraindicaciones antes de procesar el estudio.

### Episodios y actos médicos (M7 Facturación)

| Método | Endpoint | Consume | Permiso requerido |
|--------|----------|---------|-------------------|
| `GET` | `/patients/{id}/episodes` | M7 | `hce:episodes:read` |
| `GET` | `/patients/{id}/episodes/{id_ep}` | M7 | `hce:episodes:read` |
| `GET` | `/patients/{id}/episodes/{id_ep}/medical-acts` | M7 | `hce:medical-acts:read` |
| `GET` | `/patients/{id}/insurance` | M7 | `hce:insurance:read` |

### Historial del paciente (M8 Portal del Paciente)

| Método | Endpoint | Consume | Permiso requerido |
|--------|----------|---------|-------------------|
| `GET` | `/pacientes/{id}/historial/recetas` | M8 | `hce:recetas:read` |
| `GET` | `/pacientes/{id}/historial/resultados` | M8 | `hce:resultados:read` |

### Endpoints de integración M10 (Core)

| Método | Endpoint | Consume | Permiso requerido |
|--------|----------|---------|-------------------|
| `GET` | `/hce/health` | M10 | Sin auth |
| `POST` | `/hce/notify-permission-change` | M10 | Sin permiso (interno) |

### Camas e internación (M6 y uso interno)

| Método | Endpoint | Descripción | Permiso requerido |
|--------|----------|-------------|-------------------|
| `POST` | `/patients/{id}/episodes/{id_ep}/solicitudes-cama` | Crear solicitud de cama → notifica M6 | `hce:internacion:write` |
| `GET` | `/patients/{id}/episodes/{id_ep}/solicitudes-cama` | Listar solicitudes del episodio | `hce:episodes:read` |
| `POST` | `/solicitudes-cama/{id}/resolver` | Simular respuesta de M6 (dev) | `hce:internacion:write` |
| `POST` | `/solicitudes-cama/{id}/cancelar` | Cancelar solicitud pendiente | `hce:internacion:write` |
| `POST` | `/patients/{id}/episodes/{id_ep}/solicitud-internacion` | Solicitar internación directa a M6 | `hce:internacion:write` |

### Ficha médica, antecedentes y alertas (uso interno)

| Método | Endpoint | Permiso requerido |
|--------|----------|-------------------|
| `POST` | `/pacientes/{id}/ficha-medica` | `hce:ficha-medica:write` |
| `GET` | `/pacientes/{id}/ficha-medica` | `hce:ficha-medica:read` |
| `PATCH` | `/pacientes/{id}/ficha-medica` | `hce:ficha-medica:write` |
| `POST` | `/pacientes/{id}/ficha-completa` | `hce:ficha-medica:write` |
| `POST` | `/antecedentes` | `hce:antecedentes:write` |
| `GET` | `/antecedentes` | `hce:antecedentes:read` |
| `POST` | `/alertas` | `hce:alertas:write` |
| `GET` | `/alertas` | `hce:alertas:read` |

### Evoluciones y recetas (uso interno)

| Método | Endpoint | Permiso requerido |
|--------|----------|-------------------|
| `POST` | `/patients/{id}/episodes/{id_ep}/evoluciones` | `hce:evoluciones:write` |
| `GET` | `/patients/{id}/episodes/{id_ep}/evoluciones` | `hce:evoluciones:read` |
| `POST` | `/pacientes/{id}/recetas` | `hce:recetas:write` |
| `GET` | `/recetas` | `hce:recetas:read` |
| `PATCH` | `/recetas/{id}/dispensar` | `hce:recetas:write` |

---

## 7. Llamadas salientes (contratos de salida)

HCE realiza llamadas HTTP hacia los siguientes módulos. Por defecto, en desarrollo están en modo **mock** (`INTEGRATION_MODE=mock`). Setear `INTEGRATION_MODE=live` para habilitar las llamadas reales.

### HCE → M4 (Laboratorio)

**Base URL:** `http://localhost:8004/api`

| Método | Endpoint M4 | Cuándo | Payload enviado |
|--------|-------------|--------|-----------------|
| `POST` | `/v1/ordenes` | Al crear una orden de laboratorio | `{ pacienteId, medicoId, estudioIds[], prioridad, origen: "HCE" }` |
| `GET` | `/v1/estudios` | Al mostrar el catálogo de estudios disponibles | — |
| `GET` | `/v1/ordenes` | Sincronización de estado de órdenes | query params opcionales |

### HCE → M5 (Diagnóstico por Imágenes)

**Base URL:** `https://uade-da2-backend.onrender.com`

| Método | Endpoint M5 | Cuándo | Payload enviado |
|--------|-------------|--------|-----------------|
| `POST` | `/v1/webhook/orders` | Al crear una orden de imágenes | `{ id_orden_hce, id_paciente, descripcion, subtipo, modulo_origen: "modulo1_hce" }` |
| `GET` | `/v1/webhook/reportById?reportId={id}` | Cuando el webhook de M5 llega con informe incompleto | — |

### HCE → M6 (Internación y Camas)

**Base URL:** `http://localhost:8006/api`

| Método | Endpoint M6 | Cuándo | Payload enviado |
|--------|-------------|--------|-----------------|
| `POST` | `/M6/solicitudes-internacion` | Cuando el médico indica necesidad de internación | `{ id_paciente, id_episodio, id_evolucion_origen, prioridad, sector_solicitado, diagnostico_principal }` |

### HCE → M10 (Core)

**Base URL:** `http://localhost:8010/api/v1`

| Método | Endpoint Core | Cuándo | Payload enviado |
|--------|--------------|--------|-----------------|
| `GET` | `/events/types` | Al arrancar la aplicación (startup) | — |
| `POST` | `/events/subscriptions` | Al arrancar la aplicación (startup) | `{ event_type_id, subscriber_module: "modulo1_hce", endpoint_url }` |

**Suscripciones registradas al startup:**

| Evento | Webhook HCE destino |
|--------|---------------------|
| `laboratorio.resultado_listo` (M4) | `POST /api/v1/webhook/laboratorio/resultado` |
| `imagenes.reporte_finalizado` (M5) | `POST /api/v1/webhook/imagenes/reporte` |
| `turnos.presentismo` (M2) | `POST /api/v1/webhook/turnos/presentismo` |

---

## 8. Integración asincrónica — Kafka

Kafka es **opcional** en desarrollo (controlado por `ENABLE_KAFKA=false` en `.env`). Cuando está deshabilitado, los eventos se loguean localmente pero no se publican.

### HCE consume (inbound)

| Topic | Origen | Handler |
|-------|--------|---------|
| `clinica.turnos.presentismo` | M2 — Turnos | Ingresa al paciente en sala de espera |

### HCE publica (outbound)

| Topic | Destino | Cuándo |
|-------|---------|--------|
| `clinica.estudios.orden_creada` | M4, M5 | Al crear una orden de estudio |
| `clinica.hce.episodio_cerrado` | M6, M7 | Al cerrar un episodio médico |
| `clinica.hce.patologia_critica_detectada` | M10 | Al detectar patología de notificación obligatoria |

> **Nota:** La integración via REST (webhooks) y la via Kafka son **alternativas para el mismo flujo**. El mecanismo activo en producción queda a criterio de acuerdo con los grupos integrados. M2 puede elegir llamar al webhook directamente **o** publicar en Kafka; HCE soporta ambos.

---

## 9. Autenticación y autorización

### Flujo JWT

```mermaid
sequenceDiagram
    actor Usuario
    participant M10 as M10 Core
    participant HCE as M1 HCE

    Usuario->>M10: POST /auth/login (credenciales)
    M10-->>Usuario: JWT firmado (HS256, clave compartida)
    Usuario->>HCE: GET /api/v1/... + Authorization: Bearer <JWT>
    HCE->>HCE: Decodifica JWT con clave compartida
    HCE->>HCE: Valida claim de permiso requerido
    HCE-->>Usuario: 200 OK o 403 Forbidden
```

### Claims del JWT

```json
{
  "sub": 1,
  "username": "dr.perez",
  "role": "medico",
  "permissions": ["hce:read", "hce:write", "hce:ordenes:read", "..."],
  "sedeId": 3,
  "iat": 1700000000,
  "exp": 1700086400
}
```

### Permisos disponibles en HCE

| Claim | Acceso |
|-------|--------|
| `hce:read` | Lectura general |
| `hce:write` | Escritura general |
| `hce:ficha-medica:read/write` | Ficha médica permanente |
| `hce:antecedentes:read/write` | Antecedentes clínicos |
| `hce:alertas:read/write` | Alertas y alergias |
| `hce:episodes:read/write` | Episodios de atención |
| `hce:evoluciones:read/write` | Evoluciones médicas |
| `hce:recetas:read/write` | Recetas electrónicas |
| `hce:ordenes:read/write` | Órdenes de estudio |
| `hce:resultados:write` | Resultados (webhooks M4/M5) |
| `hce:internacion:write` | Internación y solicitudes de cama |
| `hce:medical-acts:read` | Actos médicos (facturación) |
| `hce:insurance:read` | Cobertura médica (facturación) |

---

## 10. Flujos principales (diagramas de secuencia)

### Flujo 1 — Llegada del paciente y atención ambulatoria

```mermaid
sequenceDiagram
    actor Paciente
    participant M2 as M2 Turnos
    participant HCE as M1 HCE
    actor Medico

    Paciente->>M2: Llega a recepción
    M2->>HCE: POST /webhook/turnos/presentismo
    HCE->>HCE: Crea registro en sala_espera (estado: ESPERANDO)
    HCE-->>M2: 202 Accepted

    Medico->>HCE: GET /sala-espera (ve la cola)
    Medico->>HCE: POST /sala-espera/{id}/llamar
    HCE->>HCE: Estado → LLAMADO

    Medico->>HCE: POST /patients/{id}/episodes (abre episodio)
    Medico->>HCE: POST /patients/{id}/episodes/{id}/evoluciones (nota clínica)
    HCE-->>Medico: Episodio + evolución creados
```

### Flujo 2 — Pedido y recepción de estudio de laboratorio

```mermaid
sequenceDiagram
    actor Medico
    participant HCE as M1 HCE
    participant M4 as M4 Laboratorio

    Medico->>HCE: POST /pacientes/{id}/ordenes/laboratorio
    HCE->>HCE: Crea orden (estado: Pendiente)
    HCE->>M4: POST /v1/ordenes (notificación async)
    M4-->>HCE: 200 OK (recibido)

    Note over M4: M4 procesa el análisis...

    alt Via webhook directo
        M4->>HCE: POST /webhook/laboratorio/resultado
        HCE->>HCE: Crea ResultadoLaboratorio + actualiza orden
        HCE-->>M4: 201 Created
    else Via bus de eventos (Core M10)
        M4->>M10: Publica laboratorio.resultado_listo
        M10->>HCE: POST /webhook/laboratorio/resultado
        HCE->>HCE: Crea ResultadoLaboratorio + actualiza orden
        HCE-->>M10: 201 Created
    end

    Note over M4: M4 también puede hacer GET /ordenes/{id}<br/>para sincronizar órdenes pendientes
```

### Flujo 3 — Internación del paciente (HCE ↔ M6)

```mermaid
sequenceDiagram
    actor Medico
    participant HCE as M1 HCE
    participant M6 as M6 Camas

    Medico->>HCE: POST /patients/{id}/episodes/{id_ep}/solicitudes-cama
    HCE->>HCE: Crea solicitud (estado: pendiente)
    HCE->>M6: POST /M6/solicitudes-internacion
    M6-->>HCE: 200 OK (solicitud recibida)

    Note over M6: M6 busca cama disponible...

    M6->>HCE: POST /internacion/ingreso
    Note right of HCE: { id_paciente, id_episodio,<br/>sector, habitacion, cama,<br/>fecha_ingreso }
    HCE->>HCE: Crea MovimientoInternacion
    HCE->>HCE: Episodio pasa a tipo "internacion"
    HCE-->>M6: 201 Created
```

### Flujo 4 — Liquidación (M7 Facturación consulta HCE)

```mermaid
sequenceDiagram
    participant M7 as M7 Facturación
    participant HCE as M1 HCE

    M7->>HCE: GET /patients/{id}/episodes?desde_fecha=...
    HCE-->>M7: Lista de episodios con resumen

    loop Por cada episodio
        M7->>HCE: GET /patients/{id}/episodes/{id_ep}/medical-acts
        HCE-->>M7: Actos médicos con codigo_nomenclador
    end

    M7->>HCE: GET /patients/{id}/insurance
    HCE-->>M7: Cobertura médica vigente (obra social)
```

---

## 11. Cómo levantar el módulo localmente

### Requisitos previos

- Docker Desktop corriendo
- Python 3.11+

### Pasos

```powershell
# 1. Levantar PostgreSQL (si no está corriendo)
docker compose up -d postgres

# 2. Activar entorno virtual
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias (solo la primera vez)
pip install -r requirements.txt

# 4. Aplicar migraciones (solo la primera vez o tras nuevas migraciones)
alembic upgrade head

# 5. Levantar el servidor
# IMPORTANTE: PYTHONUTF8=1 es necesario en Windows con Python 3.12+
$env:PYTHONUTF8 = "1"
uvicorn app.main:app --reload --port 8000
```

### URLs disponibles

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (documentación interactiva) |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/api/v1/hce/health` | Health check |
| `http://localhost:8000/api/v1/dev/simulador` | Simulador de integraciones (solo dev) |
| `http://localhost:8000/api/v1/dev/login` | Obtener JWT de desarrollo (solo dev) |

### Token de desarrollo

Para obtener un JWT válido en ambiente de desarrollo:

```bash
curl -X POST http://localhost:8000/api/v1/dev/login \
  -H "Content-Type: application/json" \
  -d "{}"
```

Responde con un `access_token` JWT con todos los permisos del rol `medico`.

---

## 12. Variables de entorno

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://hce_user:hce_pass@localhost:5432/hce_db

# JWT — debe ser la misma clave que usa M10 (Core)
JWT_SECRET_KEY=super-secret-key-compartida-con-core
JWT_ALGORITHM=HS256

# Modo de integración
# "mock"  → las llamadas salientes se simulan localmente (no hace HTTP real)
# "live"  → realiza las llamadas HTTP reales a los demás módulos
INTEGRATION_MODE=mock

# URLs de los otros módulos (solo se usan en INTEGRATION_MODE=live)
CORE_BASE_URL=http://localhost:8010/api/v1
M4_BASE_URL=http://localhost:8004/api
M5_BASE_URL=https://uade-da2-backend.onrender.com
M6_BASE_URL=http://localhost:8006/api

# URL pública de HCE (usada para registrar webhooks en el Core)
HCE_PUBLIC_URL=http://localhost:8000

# Kafka (opcional)
ENABLE_KAFKA=false
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Entorno
APP_ENV=development
APP_DEBUG=true
```

### Variable `INTEGRATION_MODE`

| Valor | Comportamiento |
|-------|---------------|
| `mock` | Las llamadas salientes a M4, M5, M6 y M10 se simulan. Los webhooks de entrada siguen funcionando normalmente. **Recomendado para desarrollo aislado.** |
| `live` | Se realizan las llamadas HTTP reales. Requiere que los módulos destino estén levantados. |

---

*Documento generado para Health Grid — Módulo 1 HCE · Puerto: 8000 · Prefijo API: `/api/v1`*
