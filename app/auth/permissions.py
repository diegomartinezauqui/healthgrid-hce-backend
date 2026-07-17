"""
Sistema de permisos basado en los claims del JWT.
Valida que el usuario tenga el permission claim requerido antes de procesar el request.
"""

from fastapi import HTTPException, status

from app.auth.jwt_handler import CurrentUser


def require_permission(required_permission: str):
    """
    Retorna una dependency que verifica que el usuario posea el permiso indicado.

    Uso en un router:
        @router.get(
            "/recetas",
            dependencies=[Depends(require_permission("hce:recetas:read"))],
        )

    O como parámetro del endpoint:
        async def get_recetas(
            user: CurrentUser = Depends(require_permission("hce:recetas:read")),
        ):
    """

    async def _check_permission(user: CurrentUser) -> CurrentUser:
        if required_permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "FORBIDDEN",
                    "message": "Su rol no tiene el permiso requerido para este recurso.",
                },
            )
        return user

    # Necesitamos que FastAPI lo reconozca como dependency con sub-dependencia
    from fastapi import Depends

    from app.auth.jwt_handler import get_current_user_from_token

    async def permission_dependency(
        user: CurrentUser = Depends(get_current_user_from_token),
    ) -> CurrentUser:
        return await _check_permission(user)

    return permission_dependency
