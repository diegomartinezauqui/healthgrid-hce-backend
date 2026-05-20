"""
Router de desarrollo — solo se registra cuando APP_ENV != "production".
Provee un endpoint de login que emula al Módulo 10 (Core) generando JWT reales.
"""

from typing import Optional

from fastapi import APIRouter

from app.auth.dev_auth import DevLoginRequest, DevLoginResponse, generate_dev_token

router = APIRouter()


@router.post(
    "/dev/login",
    response_model=DevLoginResponse,
    summary="[DEV] Obtener token JWT de desarrollo",
    description=(
        "Genera un JWT firmado con la misma clave que Core (M10). "
        "El token funciona en todos los endpoints protegidos.\n\n"
        "**Sin body**: genera token con el usuario por defecto (dr.dev, rol médico, todos los permisos).\n\n"
        "**Con body**: permite personalizar sub, username, role, permissions y duración."
    ),
)
async def dev_login(body: Optional[DevLoginRequest] = None):
    return generate_dev_token(body)
