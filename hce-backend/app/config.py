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

    # ─── JWT ──────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "super-secret-key-compartida-con-core"
    JWT_ALGORITHM: str = "HS256"

    # ─── Kafka ────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # ─── URLs de otros módulos ────────────────────────────────────
    CORE_BASE_URL: str = "http://localhost:8010/api/v1"
    M6_BASE_URL: str = "http://localhost:8006/api"

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
        "hce:resultados:write,hce:internacion:write,"
        "hce:episodes:read,hce:medical-acts:read,hce:insurance:read,"
        "hce:evoluciones:read,hce:evoluciones:write"
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
