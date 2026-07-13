import logging
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.paciente import Paciente
from app.repositories.paciente_repository import paciente_repo
from app.integrations.core_bus import _get_core_token

logger = logging.getLogger(__name__)


async def get_or_create_patient_from_core(
    db: AsyncSession, id_paciente: int
) -> Optional[Paciente]:
    """
    Busca al paciente en el cache local (pacientes).
    Si no existe, consulta al Core M10 (GET /users/{id}) y lo crea en la cache local.
    """
    # 1. Buscar en cache local
    paciente = await paciente_repo.get(db, id_paciente)
    if paciente:
        return paciente

    # 2. Si no existe, llamar al Core M10
    logger.info(
        "🔍 [Paciente Sync] Cache Miss para ID %s. Consultando al Core...", id_paciente
    )
    
    # Si las integraciones están mockeadas, creamos un paciente simulado
    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [Paciente Sync] Modo mock activo. Generando paciente mock en cache local..."
        )
        paciente = Paciente(
            id_paciente=id_paciente,
            datos_personales={
                "nombre": f"PacienteMock{id_paciente}",
                "apellido": "Simulado",
                "email": f"mock{id_paciente}@example.com",
                "dni": f"DNI{id_paciente}",
                "fecha_nacimiento": "1990-01-01",
                "genero": "Masculino",
                "obra_social": "Particular",
            },
        )
        db.add(paciente)
        await db.commit()
        return paciente

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Obtener token de la cuenta de servicio de HCE
            token = await _get_core_token(client)
            if not token:
                logger.warning(
                    "⚠️ [Paciente Sync] No se pudo obtener el token de servicio del Core."
                )
                return None

            headers = {"Authorization": f"Bearer {token}"}
            url = f"{settings.CORE_API_URL}/users/{id_paciente}"
            
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                user_data = resp.json()
                
                # Extraer datos básicos
                first_name = user_data.get("first_name", "")
                last_name = user_data.get("last_name", "")
                email = user_data.get("email", "")
                
                # Inicializar los datos_personales del paciente con campos clínicos vacíos
                datos_personales = {
                    "nombre": first_name,
                    "apellido": last_name,
                    "email": email,
                    "dni": "",
                    "fecha_nacimiento": "",
                    "genero": "",
                    "obra_social": "",
                }
                
                paciente = Paciente(
                    id_paciente=id_paciente,
                    datos_personales=datos_personales,
                )
                
                db.add(paciente)
                await db.commit()
                logger.info(
                    "✅ [Paciente Sync] Paciente %s (%s %s) creado exitosamente en la cache local.",
                    id_paciente, first_name, last_name
                )
                return paciente
            elif resp.status_code == 404:
                logger.warning(
                    "⚠️ [Paciente Sync] El usuario %s no existe en el Core.", id_paciente
                )
                return None
            else:
                logger.error(
                    "❌ [Paciente Sync] El Core respondió con error %s: %s",
                    resp.status_code, resp.text
                )
                return None
    except Exception as e:
        logger.error(
            "❌ [Paciente Sync] Error de comunicación al sincronizar paciente %s: %s",
            id_paciente, e
        )
        return None


async def get_or_create_patient_by_email(
    db: AsyncSession, email: str
) -> Optional[Paciente]:
    """
    Busca al paciente en el cache local por email.
    Si no existe, consulta al Core M10 (GET /users) y lo crea en la cache local.
    """
    from sqlalchemy import select, func

    # 1. Buscar en cache local (datos_personales ->> 'email' == email)
    result = await db.execute(
        select(Paciente).where(func.lower(Paciente.datos_personales['email'].as_string()) == func.lower(email))
    )
    paciente = result.scalar_one_or_none()
    if paciente:
        logger.info("🎯 [Paciente Sync] Cache Hit por email: %s", email)
        return paciente

    # 2. Si no existe, llamar al Core M10
    logger.info(
        "🔍 [Paciente Sync] Cache Miss por email para %s. Consultando al Core...", email
    )

    if settings.integraciones_mockeadas:
        logger.info(
            "🧪 [Paciente Sync] Modo mock activo. Generando paciente mock en cache local..."
        )
        import random
        id_mock = random.randint(10000, 99999)
        paciente = Paciente(
            id_paciente=id_mock,
            datos_personales={
                "nombre": "PacienteMock",
                "apellido": "EmailSimulado",
                "email": email,
                "dni": f"DNI{id_mock}",
                "fecha_nacimiento": "1990-01-01",
                "genero": "Masculino",
                "obra_social": "Particular",
            },
        )
        db.add(paciente)
        await db.commit()
        return paciente

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            token = await _get_core_token(client)
            if not token:
                logger.warning(
                    "⚠️ [Paciente Sync] No se pudo obtener el token de servicio del Core."
                )
                return None

            headers = {"Authorization": f"Bearer {token}"}
            # Consultar el rol de paciente (ID 10) que incluye sus usuarios asignados
            url = f"{settings.CORE_API_URL}/roles/10"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                role_data = resp.json()
                users_list = role_data.get("users", [])

                # Buscar coincidencia exacta de email
                target_user = None
                for u in users_list:
                    if u.get("email", "").lower() == email.lower():
                        target_user = u
                        break

                if target_user:
                    id_paciente = target_user["id"]
                    first_name = target_user.get("first_name", "")
                    last_name = target_user.get("last_name", "")

                    # Inicializar los datos_personales del paciente
                    datos_personales = {
                        "nombre": first_name,
                        "apellido": last_name,
                        "email": email,
                        "dni": "",
                        "fecha_nacimiento": "",
                        "genero": "",
                        "obra_social": "",
                    }

                    # Verificar si existe por ID antes de crear (por si acaso cambió de email)
                    paciente_existente = await paciente_repo.get(db, id_paciente)
                    if paciente_existente:
                        # Actualizar email local
                        paciente_existente.datos_personales["email"] = email
                        db.add(paciente_existente)
                        await db.commit()
                        return paciente_existente

                    paciente = Paciente(
                        id_paciente=id_paciente,
                        datos_personales=datos_personales,
                    )

                    db.add(paciente)
                    await db.commit()
                    logger.info(
                        "✅ [Paciente Sync] Paciente %s (%s %s) creado exitosamente por email en la cache local.",
                        id_paciente, first_name, last_name
                    )
                    return paciente
                else:
                    logger.warning(
                        "⚠️ [Paciente Sync] El usuario con email %s no existe en el Core.", email
                    )
                    return None
            else:
                logger.error(
                    "❌ [Paciente Sync] El Core respondió con error %s: %s",
                    resp.status_code, resp.text
                )
                return None
    except Exception as e:
        logger.error(
            "❌ [Paciente Sync] Error de comunicación al sincronizar por email %s: %s",
            email, e
        )
        return None
