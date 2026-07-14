"""
Configuración centralizada de la aplicación.
Lee variables de entorno desde .env usando pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del módulo HCE."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Base de datos ────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://hce_user:hce_pass@localhost:5432/hce_db"
    DB_ECHO: bool = False

    # ─── CORS ─────────────────────────────────────────────────────
    # Orígenes permitidos separados por coma. En producción colocar
    # exclusivamente el dominio del frontend desplegado.
    # Ejemplo: ALLOWED_ORIGINS=https://app.healthgrid.com,https://www.healthgrid.com
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:5173,"
        "https://healthgrid-hce-frontend-olive.vercel.app"
    )

    # ─── JWT ──────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "super-secret-key-compartida-con-core"
    JWT_ALGORITHM: str = "HS256"

    # ─── SSO / Core (M10) ─────────────────────────────────────────
    # El Core emite JWT RS256 validados por su JWKS público. HCE los acepta
    # además de los tokens HS256 internos (dev/login).
    CORE_API_URL: str = "https://api.healthcare.cantero.ar"
    CORE_JWKS_URL: str = ""  # si queda vacío se deriva de CORE_API_URL
    # Los tokens del Core traen permisos globales (users:read, ...) y NO claims
    # hce:*. Mientras el Core no emita permisos HCE, otorgamos el set completo
    # a todo usuario autenticado vía SSO para que pueda operar el módulo.
    SSO_GRANT_FULL_HCE: bool = True

    # ─── Kafka ────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # ─── URLs de otros módulos ────────────────────────────────────
    CORE_BASE_URL: str = "http://localhost:8010/api/v1"
    M6_BASE_URL: str = "http://localhost:8006/api"
    M5_BASE_URL: str = "https://uade-da2-backend.onrender.com"
    M4_BASE_URL: str = "http://localhost:8004/api"
    M7_BASE_URL: str = "https://modulo7-backend.onrender.com"
    M2_BASE_URL: str = "https://gw.healthcare.cantero.ar/api/appointments/apps2/api/v1"
    HCE_PUBLIC_URL: str = "http://localhost:8000"

    # ─── Bus de eventos del Core (RabbitMQ + POST /events/log) ────
    # Modelo real del Core: se ESCUCHA por RabbitMQ y se PUBLICA vía el Core.
    # Gateado: mientras ENABLE_CORE_BUS=False no se conecta a nada (listo para
    # enchufar cuando lleguen las credenciales del Core).
    ENABLE_CORE_BUS: bool = False
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = ""
    RABBITMQ_PASSWORD: str = ""
    RABBITMQ_VHOST: str = "/"
    # Cuenta de servicio de HCE para autenticarse al Core (POST /auth/login).
    CORE_SERVICE_EMAIL: str = ""
    CORE_SERVICE_PASSWORD: str = ""
    # Nombre base de nuestras colas (el Core agrega .requests / .responses).
    HCE_QUEUE_BASE: str = "hce"
    # IDs de evento del Core (se completan tras crear los eventos con setup_core_bus.py).
    # Mientras estén en 0 no se publica al bus (no-op).
    CORE_EVENT_ORDEN_CREADA_ID: int = 0
    CORE_EVENT_RECETA_CREADA_ID: int = 0
    CORE_EVENT_EPISODIO_CERRADO_ID: int = 0
    CORE_EVENT_PATOLOGIA_CRITICA_ID: int = 0
    # ─── Modo de integración con otros módulos ───────────────────
    # "mock" → los clients de salida loguean y devuelven respuestas canónicas
    #          (no hacen HTTP real). Webhooks de entrada siguen funcionando.
    # "live" → se realizan las llamadas HTTP reales a los otros módulos.
    INTEGRATION_MODE: str = "mock"

    # ─── Kafka opcional ──────────────────────────────────────────
    ENABLE_KAFKA: bool = False

    # ─── Aplicación ───────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # ─── Dev Auth (solo APP_ENV != production) ────────────────────
    DEV_AUTH_USER_ID: int = 1
    DEV_AUTH_USERNAME: str = "dr.dev"
    DEV_AUTH_ROLE: str = "medico"
    DEV_AUTH_SEDE_ID: int = 1
    DEV_AUTH_PERMISSIONS: str = (
        "hce:read,hce:write,"
        "hce:alertas:read,hce:alertas:write,"
        "hce:antecedentes:read,hce:antecedentes:write,"
        "hce:ficha-medica:read,hce:ficha-medica:write,"
        "hce:recetas:read,hce:recetas:write,"
        "hce:ordenes:read,hce:ordenes:write,"
        "hce:resultados:read,hce:resultados:write,hce:internacion:write,"
        "hce:episodes:read,hce:episodes:write,hce:medical-acts:read,hce:insurance:read,"
        "hce:evoluciones:read,hce:evoluciones:write"

    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def jwks_url(self) -> str:
        return self.CORE_JWKS_URL or f"{self.CORE_API_URL.rstrip('/')}/.well-known/jwks.json"

    @property
    def hce_permissions(self) -> list[str]:
        return [p.strip() for p in self.DEV_AUTH_PERMISSIONS.split(",") if p.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        """Devuelve la lista de orígenes CORS parseada desde la variable de entorno."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def integraciones_mockeadas(self) -> bool:
        return self.INTEGRATION_MODE.lower() != "live"


settings = Settings()
