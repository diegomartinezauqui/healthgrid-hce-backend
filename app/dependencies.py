from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, Request, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import CurrentUser, get_current_user_from_token
from app.database import async_session
from app.config import settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión de base de datos por request."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Type aliases para inyección limpia ──────────────────────────
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user_from_token)]


from fastapi.security import APIKeyHeader

gateway_key_scheme = APIKeyHeader(
    name="x-api-key",
    auto_error=False,
    description="Clave de seguridad del Gateway (hce-secret-key)"
)


async def verify_gateway_api_key(
    request: Request,
    x_api_key: Optional[str] = Depends(gateway_key_scheme)
):
    """
    Verifica que la petición provenga del API Gateway de seguridad validando el header x-api-key.
    Exceptúa rutas de salud, documentación y el root banner.
    """
    if not settings.ENABLE_GATEWAY_VALIDATION:
        return

    path = request.url.path
    normalized_path = path.rstrip("/")

    # Exceptuar rutas del sistema
    if (
        normalized_path == ""
        or normalized_path.endswith("/health")
        or normalized_path.endswith("/health-db")
        or "docs" in normalized_path
        or "openapi.json" in normalized_path
    ):
        return

    if x_api_key != settings.GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: la petición debe pasar por el Gateway de seguridad (x-api-key inválida)."
        )
