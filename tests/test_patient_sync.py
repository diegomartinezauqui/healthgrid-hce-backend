import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.paciente import Paciente
from app.services.core_patient_sync import get_or_create_patient_from_core


@pytest.mark.anyio
async def test_patient_sync_cache_hit(db: AsyncSession):
    # 1. Crear un paciente localmente
    paciente_local = Paciente(
        id_paciente=9999,
        datos_personales={
            "nombre": "Juan",
            "apellido": "Perez",
            "dni": "1234",
            "fecha_nacimiento": "1990-01-01",
            "genero": "Masculino",
            "obra_social": "Particular"
        }
    )
    db.add(paciente_local)
    await db.commit()

    # 2. Consultar el paciente (debe ser cache hit, sin llamadas a HTTP)
    with patch("httpx.AsyncClient.get") as mock_get:
        paciente = await get_or_create_patient_from_core(db, 9999)
        assert paciente is not None
        assert paciente.id_paciente == 9999
        assert paciente.datos_personales["nombre"] == "Juan"
        mock_get.assert_not_called()


@pytest.mark.anyio
async def test_patient_sync_cache_miss_mock_mode(db: AsyncSession):
    original_mode = settings.INTEGRATION_MODE
    settings.INTEGRATION_MODE = "mock"

    try:
        # Consultar ID inexistente (debe generar paciente mock automáticamente)
        paciente = await get_or_create_patient_from_core(db, 8888)
        assert paciente is not None
        assert paciente.id_paciente == 8888
        assert paciente.datos_personales["nombre"] == "PacienteMock8888"

        # Verificar que quedó guardado en la base de datos
        db_paciente = await db.get(Paciente, 8888)
        assert db_paciente is not None
        assert db_paciente.datos_personales["nombre"] == "PacienteMock8888"
    finally:
        settings.INTEGRATION_MODE = original_mode


@pytest.mark.anyio
async def test_patient_sync_cache_miss_live_mode_success(db: AsyncSession):
    original_mode = settings.INTEGRATION_MODE
    # Configurar modo live temporalmente
    settings.INTEGRATION_MODE = "live"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "id": 7777,
        "first_name": "Carlos",
        "last_name": "Gomez",
        "email": "carlos.gomez@example.com"
    }

    try:
        # Simulamos el login del Core
        with patch("app.services.core_patient_sync._get_core_token", return_value="fake_token"), \
             patch("httpx.AsyncClient.get", return_value=mock_response):
            
            paciente = await get_or_create_patient_from_core(db, 7777)
            assert paciente is not None
            assert paciente.id_paciente == 7777
            assert paciente.datos_personales["nombre"] == "Carlos"
            assert paciente.datos_personales["apellido"] == "Gomez"
            # Los campos clínicos de HCE deben estar vacíos por defecto
            assert paciente.datos_personales["dni"] == ""
            assert paciente.datos_personales["obra_social"] == ""

            # Verificar persistencia local
            db_paciente = await db.get(Paciente, 7777)
            assert db_paciente is not None
            assert db_paciente.datos_personales["nombre"] == "Carlos"
    finally:
        settings.INTEGRATION_MODE = original_mode


@pytest.mark.anyio
async def test_patient_sync_cache_miss_live_mode_not_found(db: AsyncSession):
    original_mode = settings.INTEGRATION_MODE
    settings.INTEGRATION_MODE = "live"

    mock_response = AsyncMock()
    mock_response.status_code = 404

    try:
        with patch("app.services.core_patient_sync._get_core_token", return_value="fake_token"), \
             patch("httpx.AsyncClient.get", return_value=mock_response):
            
            paciente = await get_or_create_patient_from_core(db, 6666)
            assert paciente is None

            # Verificar que no se guardó nada en DB
            db_paciente = await db.get(Paciente, 6666)
            assert db_paciente is None
    finally:
        settings.INTEGRATION_MODE = original_mode


from app.services.core_patient_sync import get_or_create_patient_by_email

@pytest.mark.anyio
async def test_patient_sync_by_email_cache_hit(db: AsyncSession):
    # 1. Crear un paciente localmente con email
    paciente_local = Paciente(
        id_paciente=9998,
        datos_personales={
            "nombre": "Pedro",
            "apellido": "Alvarez",
            "email": "pedro.alvarez@example.com",
            "dni": "5678",
            "fecha_nacimiento": "1992-05-05",
            "genero": "Masculino",
            "obra_social": "Particular"
        }
    )
    db.add(paciente_local)
    await db.commit()

    # 2. Consultar por email (debe ser cache hit)
    with patch("httpx.AsyncClient.get") as mock_get:
        paciente = await get_or_create_patient_by_email(db, "pedro.alvarez@example.com")
        assert paciente is not None
        assert paciente.id_paciente == 9998
        assert paciente.datos_personales["nombre"] == "Pedro"
        mock_get.assert_not_called()


@pytest.mark.anyio
async def test_patient_sync_by_email_cache_miss_mock_mode(db: AsyncSession):
    original_mode = settings.INTEGRATION_MODE
    settings.INTEGRATION_MODE = "mock"

    try:
        # Consultar por email inexistente
        paciente = await get_or_create_patient_by_email(db, "test.new@example.com")
        assert paciente is not None
        assert paciente.datos_personales["email"] == "test.new@example.com"
        assert paciente.datos_personales["nombre"] == "PacienteMock"

        # Verificar guardado local
        db_paciente = await db.get(Paciente, paciente.id_paciente)
        assert db_paciente is not None
        assert db_paciente.datos_personales["email"] == "test.new@example.com"
    finally:
        settings.INTEGRATION_MODE = original_mode


@pytest.mark.anyio
async def test_patient_sync_by_email_cache_miss_live_mode_success(db: AsyncSession):
    original_mode = settings.INTEGRATION_MODE
    settings.INTEGRATION_MODE = "live"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "id": 10,
        "name": "patient",
        "users": [
            {
                "id": 12345,
                "first_name": "Luis",
                "last_name": "Herrera",
                "email": "luis.herrera@example.com"
            }
        ]
    }

    try:
        with patch("app.services.core_patient_sync._get_core_token", return_value="fake_token"), \
             patch("httpx.AsyncClient.get", return_value=mock_response):
            
            paciente = await get_or_create_patient_by_email(db, "luis.herrera@example.com")
            assert paciente is not None
            assert paciente.id_paciente == 12345
            assert paciente.datos_personales["nombre"] == "Luis"
            assert paciente.datos_personales["email"] == "luis.herrera@example.com"

            # Verificar persistencia
            db_paciente = await db.get(Paciente, 12345)
            assert db_paciente is not None
            assert db_paciente.datos_personales["email"] == "luis.herrera@example.com"
    finally:
        settings.INTEGRATION_MODE = original_mode


@pytest.mark.anyio
async def test_patient_sync_by_email_cache_miss_live_mode_not_found(db: AsyncSession):
    original_mode = settings.INTEGRATION_MODE
    settings.INTEGRATION_MODE = "live"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: {
        "id": 10,
        "name": "patient",
        "users": [
            {
                "id": 54321,
                "first_name": "Otro",
                "last_name": "Usuario",
                "email": "otro.usuario@example.com"
            }
        ]
    }

    try:
        with patch("app.services.core_patient_sync._get_core_token", return_value="fake_token"), \
             patch("httpx.AsyncClient.get", return_value=mock_response):
            
            paciente = await get_or_create_patient_by_email(db, "no-existe@example.com")
            assert paciente is None
    finally:
        settings.INTEGRATION_MODE = original_mode
