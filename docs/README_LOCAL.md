# Levantamiento local — HCE (Historia Clínica Electrónica)

Resumen rápido
- Base de datos: PostgreSQL en contenedor Docker (configurada en `docker-compose.yml`).
- Entorno Python: usar `venv` y `requirements.txt`.
- Migraciones: `alembic` (ya configurado para async SQLAlchemy).
- Servidor API: `uvicorn` con FastAPI (routes bajo `/api/v1`).
- Kafka: opcional en desarrollo (flag `ENABLE_KAFKA` en `app/config.py` o `.env`).

Requisitos
- Docker y Docker Compose
- Python 3.11 (recomendado)
- Git (opcional)

1) Sitúate en el backend

```powershell
cd C:\Users\julia\Desktop\HCE\backend-hce\healthgrid-hce-backend\hce-backend
```

2) Levantar PostgreSQL (docker-compose)

```powershell
# Levanta solo el servicio postgres definido en docker-compose.yml
docker-compose up -d postgres
# Verifica que esté corriendo
docker ps
```

- Usuario/DB/Pass según `docker-compose.yml`:
  - Usuario: `hce_user`
  - Pass: `hce_pass`
  - DB: `hce_db`
  - Puerto local: `5432`

3) Crear y activar el entorno virtual e instalar dependencias

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4) Aplicar migraciones (Alembic)

```powershell
alembic upgrade head
```

Esto crea las tablas iniciales en `hce_db`.

5) Variables de entorno (opcional)

Crea un archivo `.env` en la raíz del backend si quieres persistir ajustes de configuración locales. Ejemplo mínimo:

```
# .env (ejemplo)
DATABASE_URL=postgresql+asyncpg://hce_user:hce_pass@localhost:5432/hce_db
ENABLE_KAFKA=false
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
APP_ENV=development
APP_DEBUG=true
```

Nota: por defecto `ENABLE_KAFKA` está en `False` en `app/config.py`. Pónlo en `true` si corres un broker Kafka local.

6) Arrancar la API (desarrollo)

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

- La API quedará disponible en: `http://127.0.0.1:8000`
- Documentación interactiva (Swagger): `http://127.0.0.1:8000/docs`

7) Comandos útiles para probar

- Health check:
```bash
curl http://127.0.0.1:8000/api/v1/hce/health
```
- Listar recetas (GET):
```bash
curl http://127.0.0.1:8000/api/v1/recetas
```
- Crear receta (ejemplo POST):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/pacientes/10500/recetas \
  -H "Content-Type: application/json" \
  -d '{"medicamento":"Amoxicilina 500mg","tipo_paciente":"Ambulatorio"}'
```

8) Acceder a la base de datos (psql dentro del contenedor)

```bash
# Abrir psql dentro del contenedor postgres
docker exec -it hce-postgres psql -U hce_user -d hce_db
# Dentro de psql
\dt
\d recetas
SELECT * FROM recetas LIMIT 10;
```

9) Ejecutar tests

```powershell
.\venv\Scripts\Activate.ps1
pytest -q
```

10) Notas sobre Kafka
- Kafka está ahora configurado como opcional. Si lo habilitas (`ENABLE_KAFKA=true`) el backend intentará conectar con `KAFKA_BOOTSTRAP_SERVERS`.
- Si Kafka no está disponible, el backend arranca igual y los eventos se loguean localmente.

11) Archivos y cambios clave realizados (referencia)
- `app/schemas/receta.py`: añadido `ItemRecetaSchema` y `ItemRecetaCreate`.
- `app/main.py`: añadido `CORSMiddleware`, control de arranque/shutdown de Kafka con flag `ENABLE_KAFKA`.
- `app/services/kafka_producer.py` y `app/kafka/consumer.py`: manejo robusto de fallos de Kafka.
- `frontend/src/services/api.js`: baseURL ajustada a `/api/v1` (frontend local).
