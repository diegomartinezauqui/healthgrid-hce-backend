"""
Generación de JWT para desarrollo local.
Emula el token que en producción emitiría el Módulo 10 (Core).

Solo se registra como endpoint cuando APP_ENV != "production".
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from jose import jwt
from pydantic import BaseModel, Field

from app.config import settings


class DevLoginRequest(BaseModel):
    """
    Body opcional para personalizar el token de desarrollo.
    Si no se envía ningún campo, se usan los valores por defecto de settings.
    """

    sub: Optional[int] = Field(None, description="ID del usuario (médico)", examples=[1])
    username: Optional[str] = Field(None, description="Nombre de usuario", examples=["dr.dev"])
    role: Optional[str] = Field(None, description="Rol del usuario", examples=["medico"])
    permissions: Optional[List[str]] = Field(
        None,
        description="Lista de permisos",
        examples=[[
            "hce:read", "hce:write",
            "hce:alertas:read", "hce:alertas:write",
            "hce:antecedentes:read", "hce:antecedentes:write",
            "hce:ficha-medica:read", "hce:ficha-medica:write",
            "hce:recetas:read", "hce:recetas:write", "hce:ordenes:read",
            "hce:resultados:write", "hce:internacion:write",
            "hce:episodes:read", "hce:episodes:write", "hce:medical-acts:read", "hce:insurance:read",
            "hce:evoluciones:read", "hce:evoluciones:write"
        ]],
    )
    sede_id: Optional[int] = Field(None, description="ID de la sede", examples=[1])
    expire_hours: Optional[int] = Field(
        None,
        description="Horas de validez del token (default: 24)",
        examples=[24],
    )


class DevLoginResponse(BaseModel):
    """Respuesta del endpoint de login de desarrollo."""

    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int
    user: dict


def generate_dev_token(request: Optional[DevLoginRequest] = None) -> DevLoginResponse:
    """
    Genera un JWT firmado con la misma clave que usa Core (JWT_SECRET_KEY).
    El token resultante pasa por el mismo decode_jwt() que cualquier token real.
    """
    data = request or DevLoginRequest()

    sub = data.sub or settings.DEV_AUTH_USER_ID
    username = data.username or settings.DEV_AUTH_USERNAME
    role = data.role or settings.DEV_AUTH_ROLE
    sede_id = data.sede_id or settings.DEV_AUTH_SEDE_ID
    expire_hours = data.expire_hours or 24
    permissions = data.permissions or [
        p.strip() for p in settings.DEV_AUTH_PERMISSIONS.split(",") if p.strip()
    ]

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),  # JWT estándar: sub debe ser string
        "username": username,
        "role": role,
        "permissions": permissions,
        "sedeId": sede_id,
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return DevLoginResponse(
        access_token=token,
        expires_in_hours=expire_hours,
        user={
            "sub": sub,
            "username": username,
            "role": role,
            "permissions": permissions,
            "sedeId": sede_id,
        },
    )
