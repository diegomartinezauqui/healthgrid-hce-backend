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

    sub: int                    # ID del usuario (médico)
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
    Acepta dos tipos de token:
      - HS256 interno (POST /api/v1/dev/login) — validado con la clave compartida.
      - RS256 del Core (SSO) — validado con el JWKS público del Core.
    Retorna un CurrentUser con los datos del payload.
    """
    token = credentials.credentials

    # Detectamos el algoritmo por el header (sin verificar todavía).
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Token JWT malformado."},
        )

    # ── Token del Core (SSO) ──
    if alg == "RS256":
        from app.auth.jwks import decode_core_jwt

        payload = await decode_core_jwt(token)
        user_id = payload.get("user_id", payload.get("sub"))
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "UNAUTHORIZED", "message": "El token del Core no trae user_id."},
            )
        permisos = list(payload.get("permissions", []))
        # El Core aún no emite claims hce:*; otorgamos el set HCE completo.
        if settings.SSO_GRANT_FULL_HCE:
            permisos = sorted(set(permisos) | set(settings.hce_permissions))
        return CurrentUser(
            sub=int(user_id),
            username=str(payload.get("email", payload.get("username", ""))),
            role=payload.get("role", "medico"),
            permissions=permisos,
            sede_id=int(payload.get("sedeId", settings.DEV_AUTH_SEDE_ID)),
        )

    # ── Token interno HS256 ──
    payload = decode_jwt(token)
    try:
        return CurrentUser(
            sub=int(payload["sub"]),
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
