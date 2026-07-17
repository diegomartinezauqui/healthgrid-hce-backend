"""
Validación de JWT RS256 emitidos por el Core (M10) usando su JWKS público.

El Core publica sus claves en {CORE_API_URL}/.well-known/jwks.json. Cacheamos el
JWKS en memoria (con TTL) y validamos firma RS256 + expiración localmente, sin
llamar al Core en cada request. Ver guía SSO del Core.
"""

import time
from typing import Optional

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings

_JWKS_TTL_SECONDS = 3600
_cache: dict = {"keys": None, "ts": 0.0}


async def _fetch_jwks(force: bool = False) -> dict:
    now = time.time()
    if not force and _cache["keys"] is not None and (now - _cache["ts"]) < _JWKS_TTL_SECONDS:
        return _cache["keys"]
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(settings.jwks_url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        if _cache["keys"] is not None:
            return _cache["keys"]  # usar cache vieja si el Core no responde
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "SSO_UNAVAILABLE", "message": f"No se pudo obtener el JWKS del Core: {exc}"},
        )
    _cache["keys"] = data
    _cache["ts"] = now
    return data


def _find_key(jwks: dict, kid: Optional[str]) -> Optional[dict]:
    for key in (jwks or {}).get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def decode_core_jwt(token: str) -> dict:
    """
    Valida un JWT RS256 del Core contra su JWKS y devuelve el payload.
    Lanza 401 si la firma es inválida, expiró o no se encuentra la clave.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Token JWT malformado."},
        )

    kid = header.get("kid")
    jwks = await _fetch_jwks()
    key = _find_key(jwks, kid)
    if key is None:
        # Posible rotación de claves: refrescar una vez.
        jwks = await _fetch_jwks(force=True)
        key = _find_key(jwks, kid)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "No se encontró la clave pública del Core para este token."},
        )

    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # el token del Core hoy no trae aud/iss
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Token del Core inválido o expirado."},
        )
