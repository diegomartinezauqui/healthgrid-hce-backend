# Configuración de Variables de Entorno (Backend HCE)

Este documento detalla todas las variables de entorno necesarias para configurar el Backend de la Historia Clínica Electrónica (HCE), tanto para desarrollo local como para el despliegue en producción (Render).

---

## ─── URLs de otros módulos (Integraciones REST) ───────────────
CORE_BASE_URL=http://localhost:8010/api/v1
M6_BASE_URL=http://localhost:8006/api
M5_BASE_URL=https://uade-da2-backend.onrender.com
M4_BASE_URL=http://localhost:8004/api
M7_BASE_URL=http://localhost:8007
HCE_PUBLIC_URL=http://localhost:8000

## 🔑 1. Variables del Servidor y Base de Datos

* **`DATABASE_URL`**:
  * **Descripción**: URL de conexión para la base de datos PostgreSQL utilizando el driver asíncrono `asyncpg`.
  * **Valor Local (Docker)**: `postgresql+asyncpg://hce_user:hce_pass@localhost:5432/hce_db`
  * **Valor Producción (Aiven)**: `postgresql+asyncpg://avnadmin:<contraseña>@<host>:<puerto>/defaultdb?ssl=require`

* **`APP_ENV`**:
  * **Descripción**: Entorno en el que se ejecuta la aplicación. Desactiva los endpoints simuladores en producción.
  * **Valores**: `development` | `production`

* **`APP_DEBUG`**:
  * **Descripción**: Habilita o deshabilita los logs de depuración (debug) del servidor y el ORM.
  * **Valores**: `True` | `False`

* **`INTEGRATION_MODE`**:
  * **Descripción**: Modo de comunicación con otros módulos.
  * **Valores**: 
    * `mock` (Desarrollo local: simula respuestas canónicas y no realiza peticiones HTTP reales a otros servidores).
    * `live` (Producción: ejecuta las llamadas HTTP reales hacia los endpoints externos).

---

## 🔒 2. Variables de SSO y Autenticación (Core M10)

El backend valida tokens de forma asimétrica descargando las claves públicas (JWKS) del Core.

* **`CORE_API_URL`**:
  * **Descripción**: URL base del Core en producción para derivar la ruta de descarga del JWKS.
  * **Valor**: `https://api.healthcare.cantero.ar`

* **`CORE_JWKS_URL`**:
  * **Descripción**: Opcional. URL directa para descargar el archivo JSON de claves públicas. Si queda vacía, se asume por defecto `{CORE_API_URL}/.well-known/jwks.json`.
  * **Valor**: *(Dejar en blanco)*

* **`SSO_GRANT_FULL_HCE`**:
  * **Descripción**: Permite saltearse la restricción de permisos vacíos del Core durante la fase de integración. Otorga todos los permisos del módulo HCE a cualquier token válido firmado por el Core.
  * **Valor**: `True`

---

## 📡 3. Variables de RabbitMQ e Integración del Core Bus

Maneja el envío de eventos vía HTTP al Core y la escucha asíncrona mediante colas de RabbitMQ.

* **`ENABLE_CORE_BUS`**:
  * **Descripción**: Activa el consumidor de RabbitMQ y el publicador de eventos al Core. **Debe estar en `False` en desarrollo local si no se tiene configurada la infraestructura.**
  * **Valores**: `True` | `False`

* **`RABBITMQ_HOST`**: Servidor de RabbitMQ provisto por el Core.
* **`RABBITMQ_PORT`**: Puerto de conexión a RabbitMQ (por defecto `5672`).
* **`RABBITMQ_USER`**: Email del usuario de RabbitMQ provisto por el Core.
* **`RABBITMQ_PASSWORD`**: Contraseña del usuario de RabbitMQ.
* **`RABBITMQ_VHOST`**: Virtual Host configurado (usualmente `/`).
* **`HCE_QUEUE_BASE`**: Nombre base para las colas de HCE. Generará automáticamente `hce.requests` y `hce.responses` (por defecto `hce`).

* **`CORE_SERVICE_EMAIL`**: Email de la cuenta de servicio de HCE en el Core (requerido para publicar eventos).
* **`CORE_SERVICE_PASSWORD`**: Contraseña de la cuenta de servicio de HCE en el Core.

---

## 🆔 4. IDs de Eventos del Core

IDs numéricos generados por el Core para identificar las transacciones de HCE (se completan tras correr el script de setup).

* **`CORE_EVENT_RECETA_CREADA_ID`**: ID del evento `hce.receta.creada`.
* **`CORE_EVENT_ORDEN_CREADA_ID`**: ID del evento `hce.orden.creada`.
* **`CORE_EVENT_EPISODIO_CERRADO_ID`**: ID del evento `hce.episodio.cerrado`.
* **`CORE_EVENT_PATOLOGIA_CRITICA_ID`**: ID del evento `hce.notificacion.obligatoria`.
