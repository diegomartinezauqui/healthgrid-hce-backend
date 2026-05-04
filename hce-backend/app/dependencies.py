"""
Dependencies inyectables para FastAPI.
Provee la sesión de BD y el usuario autenticado actual.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import CurrentUser, get_current_user_from_token
from app.database import async_session


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
