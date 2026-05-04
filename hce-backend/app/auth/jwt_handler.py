"""
Manejo de JWT emitido por Módulo 10 (Core).
HCE NO emite tokens — solo los valida localmente usando la clave compartida.
"""

from dataclasses import dataclass
from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

# ─── Esquema de seguridad Bearer ─────────────────────────────────
security = HTTPBearer(
    scheme_name="JWT Bearer",
    description="JWT emitido por Módulo 10 (Core). Header: Authorization: Bearer <token>",
)


@dataclass
class CurrentUser:
    """Datos del usuario extraídos del JWT payload."""

    sub: int                    # ID del usuario
    username: str
    role: str                   # medico, enfermero, administrativo, etc.
    permissions: List[str]      # ["hce:read", "hce:write", ...]
    sede_id: int


def decode_jwt(token: str) -> dict:
    """
    Decodifica y valida un JWT usando la clave secreta de Core.
    Lanza HTTPException 401 si es inválido o expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Token JWT inválido o expirado. Solicite un nuevo token.",
            },
        )


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Dependency de FastAPI que extrae y valida el JWT del header Authorization.
    Retorna un CurrentUser con los datos del payload.
    """
    payload = decode_jwt(credentials.credentials)

    try:
        return CurrentUser(
            sub=payload["sub"],
            username=payload.get("username", ""),
            role=payload.get("role", ""),
            permissions=payload.get("permissions", []),
            sede_id=payload.get("sedeId", 0),
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Token JWT con payload incompleto.",
            },
        )
