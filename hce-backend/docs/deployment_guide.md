# Guía de Despliegue en Render y Pruebas Local-Nube

Esta guía contiene los pasos detallados para configurar y desplegar el Backend de HCE en Render y cómo realizar pruebas de integración usando el Frontend y Backend corriendo de forma local conectados a la base de datos PostgreSQL alojada en Aiven.

---

## 📋 Parte 1: Paso a Paso del Despliegue en Render

Sigue estos pasos en tu cuenta de Render:

1. **Crear un nuevo servicio en Render**:
   * En tu dashboard de Render, haz clic en **New +** y selecciona **Web Service**.
   * Conecta tu repositorio de GitHub correspondiente al backend de HCE (`healthgrid-hce-backend`).

2. **Configurar los datos del servicio**:
   * **Name**: `healthgrid-hce-backend` (o el nombre que prefieras).
   * **Region**: Selecciona la más cercana a tu base de datos de Aiven (usualmente `Ohio` o `Frankfurt`).
   * **Branch**: `main`.
   * **Runtime**: `Python`.

3. **Comandos de construcción e inicio**:
   * **Build Command**: 
     ```bash
     pip install -r requirements.txt && alembic upgrade head
     ```
     *(Esto instalará las dependencias y aplicará las migraciones automáticamente con cada despliegue).*
   * **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

4. **Configurar las Variables de Entorno (Environment)**:
   Ve a la pestaña **Environment** dentro del servicio creado, haz clic en **Add Environment Variable** e introduce los siguientes pares clave-valor:
   
   | Variable | Valor | Descripción |
   | :--- | :--- | :--- |
   | `DATABASE_URL` | `postgresql+asyncpg://avnadmin:AVNS_6KBcQthuGkKaHkduo-f@pg-b3f7bce-montinahuel-1c23.d.aivencloud.com:11948/defaultdb?ssl=require` | Conexión segura a Aiven |
   | `APP_ENV` | `production` (o `development` si deseas mantener los simuladores `/dev/`) | Entorno de ejecución |
   | `INTEGRATION_MODE` | `live` (o `mock` si deseas simular llamadas a otros módulos) | Modo de integración con el resto de módulos |
   | `CORE_BASE_URL` | *[URL de producción del Core]* | Ruta de autenticación |
   | `M4_BASE_URL` | *[URL de producción de M4 Laboratorio]* | Ruta de bioquímica |
   | `M5_BASE_URL` | *[URL de producción de M5 Imágenes]* | Ruta de PACS/Imágenes |
   | `M6_BASE_URL` | *[URL de producción de M6 Internación]* | Ruta de camas |

5. **Guardar cambios y Desplegar**:
   * Haz clic en **Save Changes**. Render iniciará automáticamente la construcción y el despliegue del backend.

---

## 🧪 Parte 2: Pruebas Locales Conectados a la Nube

Para verificar que todo funcione correctamente antes del despliegue final, podemos correr el Backend localmente apuntando a la base de datos de Aiven, y conectar el Frontend a dicho backend.

### Paso 1: Cargar los pacientes de prueba en Aiven (Seeding)
La base de datos de Aiven actualmente está vacía. Debemos sembrar los pacientes con IDs `3001` a `3005` para que se puedan consultar desde el sistema.
* *Nota: Los datos ya fueron cargados mediante un script asíncrono.*

### Paso 2: Ejecutar el Backend en tu máquina local
Dado que ya configuramos la URI de Aiven en el archivo local `.env`, simplemente inicia el servidor:
1. Abre tu terminal en el proyecto backend (`healthgrid-hce-backend\hce-backend`).
2. Activa el entorno virtual:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. Levanta el servidor FastAPI:
   ```powershell
   uvicorn app.main:app --reload
   ```
   *(El backend quedará escuchando en `http://localhost:8000`)*

### Paso 3: Iniciar el Frontend
1. Abre tu terminal de desarrollo en la carpeta del Frontend de la Historia Clínica.
2. Asegúrate de que la configuración de API (`api.js` o `.env` del frontend) apunte al backend local: `http://localhost:8000/api/v1`.
3. Ejecuta el servidor de desarrollo del front (generalmente `npm run dev` o `npm start`).
4. Abre la aplicación en tu navegador.

### Paso 4: Validar en el Simulador y la Aplicación
1. Ve a `http://localhost:8000/dev/simulador`.
2. Prueba a registrar presentismo, crear recetas o ingresar pacientes. Verás que los registros se graban directamente en Aiven de forma transparente y segura.
