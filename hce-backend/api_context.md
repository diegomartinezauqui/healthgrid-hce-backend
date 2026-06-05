# HCE Backend - Contexto de Desarrollo, Arquitectura y Entidades

Este documento es el mapa de contexto técnico completo para el Módulo 1: Historia Clínica Electrónica (HCE). Permite a desarrolladores y agentes de IA comprender de forma inmediata todo el desarrollo del backend, incluyendo su modelo de datos relacional, flujos de seguridad, endpoints, reglas de diseño de APIs e integración.

---

## 1. Arquitectura y Estructura del Proyecto

El backend está desarrollado sobre **FastAPI** y estructurado bajo una arquitectura multicapa desacoplada:

* **`/app/models`**: Modelos ORM de SQLAlchemy. Definen la estructura de la base de datos relacional.
* **`/app/repositories`**: Capa de abstracción de datos (Patrón Repositorio). Hereda operaciones CRUD genéricas de una clase `BaseRepository` para evitar duplicación de queries SQLAlchemy.
* **`/app/services`**: Capa lógica de negocio. Orquesta validaciones clínicas, procesamiento de datos y llamadas entre repositorios.
* **`/app/routers`**: Capa de presentación / controladores REST. Expone las rutas, define parámetros de entrada/salida (Schemas Pydantic) y declara los permisos requeridos.
* **`/app/schemas`**: Schemas de validación Pydantic. Separan los modelos de entrada de la API (`Create`/`Update`) de los modelos serializados de respuesta (`Response`).
* **`/app/auth`**: Mapea la seguridad perimetral. HCE no emite tokens (los emite el Módulo 10 - Core); HCE los decodifica de forma simétrica (`JWT_SECRET_KEY`) y controla los accesos basados en claims de permisos.
* **`/tests`**: Pruebas automáticas utilizando `pytest` y base de datos SQLite efímera para testeo veloz y aislado.

---

## 2. Modelo de Datos y Entidades (Base de Datos)

El sistema define 12 entidades relacionales conectadas al paciente como eje central. A continuación se detallan los campos clave, tipos y relaciones de cada una:

```
                  ┌──────────────────────┐
                  │       PACIENTE       │
                  └──────────┬───────────┘
         ┌───────────────────┼─────────────────────┐
         ▼                   ▼                     ▼
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │ FICHA MEDICA │     │   EPISODIO   │     │   ALERTA     │
 └──────────────┘     └──────┬───────┘     └──────────────┘
                             ├─────────────────────┐
                             ▼                     ▼
                      ┌──────────────┐      ┌──────────────┐
                      │ ACTO MEDICO  │      │ MOV. INTERN. │
                      └──────────────┘      └──────────────┘
```

### 2.1 Paciente (`Paciente`)
* **Tabla**: `pacientes`
* **Campos**:
  * `id_paciente` (PK, Integer, index=True): Identificador único del paciente (mantenido en sincronía con el M10).
  * `datos_personales` (JSONB / JSON): Diccionario con datos demográficos (nombre, apellido, DNI, fecha de nacimiento, etc.).
  * `created_at` / `updated_at` (DateTime, con Zona Horaria UTC).
* **Relaciones**:
  * `ficha_medica` (FichaMedica, One-to-One).
  * `episodios` (List[Episodio], One-to-Many).
  * `alertas` (List[AlertaClinicaPaciente], One-to-Many).
  * `antecedentes` (List[AntecedentePaciente], One-to-Many).
  * `recetas` (List[Receta], One-to-Many).
  * `ordenes` (List[Orden], One-to-Many).
  * `resultados` (List[Resultado], One-to-Many).
  * `coberturas` (List[CoberturaMedica], One-to-Many).

### 2.2 Ficha Médica (`FichaMedica`)
* **Tabla**: `fichas_medicas`
* **Descripción**: Almacena datos clínicos semipermanentes del paciente.
* **Campos**:
  * `id_paciente` (PK, FK a `pacientes.id_paciente`, Integer).
  * `grupo_sanguineo` (String(10), nullable=True): ej. "0+", "A-".
  * `peso_kg` (Numeric(5, 2), nullable=True).
  * `altura_cm` (Numeric(5, 2), nullable=True).
  * `observaciones_generales` (Text, nullable=True).

### 2.3 Episodio Clínico (`Episodio`)
* **Tabla**: `episodios`
* **Descripción**: Representa una atención o tránsito clínico (una consulta externa, una internación, una visita de guardia).
* **Campos**:
  * `id_episodio` (PK, Integer, autoincrement=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `tipo` (Enum `TipoEpisodio`): `"consulta"`, `"internacion"`, `"guardia"`, `"cirugia"`.
  * `estado` (Enum `EstadoEpisodio`): `"open"`, `"closed"` (Default: `open`).
  * `id_sede` (Integer): ID del centro médico donde se atiende.
  * `id_medico_responsable` (Integer): ID del médico asignado.
  * `diagnostico_principal` (String(500), nullable=True).
  * `fecha_apertura` (DateTime con Zona Horaria UTC).
  * `fecha_cierre` (DateTime con Zona Horaria UTC, nullable=True).
* **Relaciones**:
  * `actos_medicos` (List[ActoMedico], One-to-Many, lazy="selectin").
  * `movimientos` (List[MovimientoInternacion], One-to-Many, lazy="selectin").

### 2.4 Evolución (`Evolucion`)
* **Tabla**: `evoluciones`
* **Descripción**: Notas clínicas redactadas por los profesionales de salud en cada encuentro.
* **Campos**:
  * `id_evolucion` (PK, Integer, autoincrement=True).
  * `id_episodio` (FK a `episodios.id_episodio`, Integer, index=True).
  * `id_profesional` (Integer): ID del profesional que redacta la nota.
  * `contenido` (Text, nullable=True).
  * `fecha` (DateTime con Zona Horaria UTC, default=func.now()).
* **Relaciones**:
  * `recetas` (List[Receta], One-to-Many, lazy="selectin").

### 2.5 Acto Médico / Prestación (`ActoMedico`)
* **Tabla**: `actos_medicos`
* **Descripción**: Procedimientos, consultas o prestaciones realizadas durante un episodio clínico.
* **Campos**:
  * `id_acto_medico` (PK, Integer, autoincrement=True).
  * `id_episodio` (FK a `episodios.id_episodio`, Integer, index=True).
  * `codigo_nomenclador` (String(20), nullable=True): Código estándar de facturación.
  * `descripcion` (String(500), nullable=True).
  * `tipo` (Enum `TipoActoMedico`): `"consulta"`, `"procedimiento"`, `"laboratorio"`, `"imagen"`, `"otro"`.
  * `id_profesional` (Integer, nullable=True): ID del profesional que realizó el acto.
  * `fecha_realizacion` (DateTime con Zona Horaria UTC).
  * `cantidad` (Integer, default=1).
  * `observaciones` (Text, nullable=True).

### 2.6 Alerta Clínica (`AlertaClinicaPaciente`)
* **Tabla**: `alerta_clinica_paciente`
* **Descripción**: Condiciones de alto riesgo del paciente (alergias graves, contraindicaciones de medicamentos).
* **Campos**:
  * `id` (PK, Integer, autoincrement=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `tipo` (Enum `TipoConsideracion`): `"alergia"`, `"contraindicacion"`, `"patologia_critica"`, `"otra"`.
  * `severidad` (Enum `SeveridadAlerta`): `"leve"`, `"moderada"`, `"alta"`.
  * `descripcion` (Text): Detalles de la alerta.
  * `estado` (Enum `EstadoAlerta`): `"activa"`, `"resuelta"`.
  * `fecha_registro` (DateTime con Zona Horaria UTC).
  * `id_medico_registro` (Integer).
  * `fecha_resolucion` (DateTime con Zona Horaria UTC, nullable=True).
  * `id_medico_resolucion` (Integer, nullable=True).
  * `motivo_resolucion` (Text, nullable=True).

### 2.7 Antecedente Clínico (`AntecedentePaciente`)
* **Tabla**: `antecedente_paciente`
* **Descripción**: Historial médico no urgente (antecedentes familiares, quirúrgicos, patológicos o hábitos de vida).
* **Campos**:
  * `id` (PK, Integer, autoincrement=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `tipo` (Enum `TipoAntecedente`): `"patologico"`, `"quirurgico"`, `"familiar"`, `"habito"`, `"otro"`.
  * `descripcion` (Text).
  * `fecha_suceso` (Date, nullable=True).
  * `observaciones` (Text, nullable=True).
  * `fecha_registro` (DateTime con Zona Horaria UTC).
  * `id_medico_registro` (Integer).

### 2.8 Movimiento de Internación (`MovimientoInternacion`)
* **Tabla**: `movimientos_internacion`
* **Descripción**: Cambios de cama/habitación dentro de un episodio de internación (Integración con M6).
* **Campos**:
  * `id_movimiento` (PK, Integer, autoincrement=True).
  * `id_episodio` (FK a `episodios.id_episodio`, Integer, index=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `sector` (String(100)): ej. "UTI", "Sala Común B".
  * `habitacion` (String(100), nullable=True).
  * `cama` (String(50)).
  * `fecha_ingreso` (DateTime con Zona Horaria UTC).
  * `medico_solicitante` (String(200), nullable=True).

### 2.9 Receta (`Receta`)
* **Tabla**: `recetas`
* **Descripción**: Medicamentos recetados asociados a una evolución clínica (Integración con M3).
* **Campos**:
  * `id_receta` (PK, Integer, autoincrement=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `id_evolucion` (FK a `evoluciones.id_evolucion`, Integer, index=True).
  * `medicamento` (String(300)): Nombre del principio activo o marca comercial.
  * `indicaciones` (Text, nullable=True).
  * `estado` (Enum `EstadoReceta`): `"activa"`, `"archivada"`, `"cancelada"`.

### 2.10 Orden Médica (`Orden`)
* **Tabla**: `ordenes`
* **Descripción**: Pedidos de estudios diagnósticos (análisis clínicos, radiografías) (Integración M4/M5).
* **Campos**:
  * `id_orden` (PK, Integer, autoincrement=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `tipo_estudio` (Enum `TipoEstudio`): `"laboratorio"`, `"imagen"`, `"cardiologia"`, `"otro"`.
  * `descripcion_pedido` (String(500), nullable=True).
  * `prioridad` (Enum `PrioridadOrden`): `"baja"`, `"media"`, `"alta"`.
  * `estado` (String(50), default="Pendiente").

### 2.11 Resultado de Estudio (`Resultado`)
* **Tabla**: `resultados`
* **Descripción**: Informe de los estudios realizados al paciente (Integración M4/M5).
* **Campos**:
  * `id_resultado` (PK, Integer, autoincrement=True).
  * `id_orden` (Integer, nullable=True): ID de la orden originaria.
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `tipo_estudio` (Enum `TipoEstudio`).
  * `id_profesional_firmante` (String(200)).
  * `fecha_resultado` (DateTime con Zona Horaria UTC).
  * `informe` (Text): Descripción textual del resultado del estudio.
  * `path_archivo` (String(500), nullable=True): Ruta a almacenamiento físico del PDF/imagen.

### 2.12 Cobertura Médica (`CoberturaMedica`)
* **Tabla**: `coberturas_medicas`
* **Descripción**: Caché local de la cobertura del paciente para consumo de Facturación (M7).
* **Campos**:
  * `id` (PK, Integer, autoincrement=True).
  * `id_paciente` (FK a `pacientes.id_paciente`, Integer, index=True).
  * `id_obra_social` (Integer).
  * `nombre_obra_social` (String(200)).
  * `codigo_plan` (String(50), nullable=True).
  * `numero_afiliado` (String(50), nullable=True).
  * `vigente_desde` / `vigente_hasta` (Date, nullable=True).

---

## 3. Normas de Compatibilidad de Base de Datos para SQLite (Tests)

Para evitar roturas de la suite de tests al utilizar SQLite (`test.db` en local), se deben cumplir estrictamente estas dos reglas al modificar o crear nuevos modelos de SQLAlchemy:

1. **Evitar tipo JSONB crudo**: SQLite no lo soporta. Se debe mapear con `.with_variant(JSONB(), "postgresql")`:
   ```python
   datos_personales: Mapped[dict | None] = mapped_column(
       JSON().with_variant(JSONB(), "postgresql"), nullable=True
   )
   ```
2. **Evitar Enums nativos en base de datos**: SQLite guarda los Enums como texto ordinario. Debes proveer `values_callable` en la declaración del Enum de SQLAlchemy:
   ```python
   estado: Mapped[EstadoEpisodio] = mapped_column(
       Enum(EstadoEpisodio, name="estado_episodio", values_callable=lambda x: [e.value for e in x])
   )
   ```

---

## 4. Inyección de JWT, Permisos y Entorno Local

### Decodificación y `CurrentUser`
FastAPI decodifica los tokens en la dependencia [app/auth/jwt_handler.py](file:///c:/Users/monti/Desktop/Desarrollo_de_apps_ii/healthgrid-hce-backend/hce-backend/app/auth/jwt_handler.py#L55). Esta dependencia inyecta el modelo `CurrentUser` con el `sub` (parseado a `int`), rol, permisos y `sede_id`.

### Sistema de Login de Desarrollo (Mock)
Cuando `APP_ENV != production`, en el router [dev.py](file:///c:/Users/monti/Desktop/Desarrollo_de_apps_ii/healthgrid-hce-backend/hce-backend/app/routers/dev.py) se expone:
* **`POST /api/v1/dev/login`**: Firma un token JWT simulado usando la misma clave secreta de producción.
* Si el body se envía vacío, usa un usuario médico mock por defecto. También permite inyectar roles, un array de `permissions` customizados y un `sedeId` específico para testing.

---

## 5. Endpoints, Permisos y Payloads de Consulta/Registro

### 5.1 Episodios y Actos Médicos (Atención Clínica)

* **`GET /api/v1/patients/{id_paciente}/episodes`**: Lista episodios de un paciente.
  * **Permiso**: `hce:episodes:read`
  * **Query Params (Opcionales)**: `estado` (str, ej: "open"), `desde_fecha` (date, YYYY-MM-DD), `hasta_fecha` (date, YYYY-MM-DD).

* **`POST /api/v1/patients/{id_paciente}/episodes`**: Abre un nuevo episodio clínico para el paciente.
  * **Permiso**: `hce:episodes:write`
  * **Body (`EpisodioCreate`)**:
    ```json
    {
      "tipo": "consulta",              // Requerido. Enum: "consulta", "internacion", "guardia", "cirugia"
      "diagnostico_principal": "string",// Opcional
      "id_sede": 1                     // Opcional. Si se omite, se hereda la sede del JWT
    }
    ```

* **`GET /api/v1/patients/{id_paciente}/episodes/{id_episodio}`**: Detalle de episodio con sus prestaciones.
  * **Permiso**: `hce:episodes:read`

* **`PATCH /api/v1/patients/{id_paciente}/episodes/{id_episodio}`**: Actualiza o cierra un episodio clínico.
  * **Permiso**: `hce:episodes:write`
  * **Body (`EpisodioUpdate`)** (todos los campos opcionales):
    ```json
    {
      "tipo": "consulta",
      "estado": "closed",              // Enum: "open", "closed". Si es "closed", registra automaticamente la fecha de cierre.
      "id_sede": 1,
      "id_medico_responsable": 42,
      "diagnostico_principal": "string"
    }
    ```

* **`GET /api/v1/patients/{id_paciente}/episodes/{id_episodio}/medical-acts`**: Lista actos médicos de un episodio.
  * **Permiso**: `hce:medical-acts:read`

* **`POST /api/v1/patients/{id_paciente}/episodes/{id_episodio}/medical-acts`**: Registra una prestación/acto médico dentro de un episodio activo.
  * **Permiso**: `hce:medical-acts:write`
  * **Body (`ActoMedicoCreate`)**:
    ```json
    {
      "codigo_nomenclador": "01.01.01", // Opcional (Max. 20 caracteres)
      "descripcion": "string",          // Opcional (Max. 500 caracteres)
      "tipo": "consulta",               // Requerido. Enum: "consulta", "procedimiento", "laboratorio", "imagen", "otro"
      "id_profesional": 42,             // Opcional. Si se omite, se hereda el sub del JWT
      "fecha_realizacion": "2026-06-04T19:54:00Z", // Opcional (DateTime ISO, default: actual)
      "cantidad": 1,                    // Opcional (default: 1, min: 1)
      "observaciones": "string"         // Opcional
    }
    ```
    *Nota: Lanza un error `422 Unprocessable Entity` si el episodio se encuentra cerrado.*

---

### 5.2 Ficha Médica, Alertas y Antecedentes

* **`GET /api/v1/pacientes/{id_paciente}/ficha-medica`**: Obtiene la ficha médica de un paciente.
  * **Permiso**: `hce:ficha-medica:read`

* **`POST /api/v1/pacientes/{id_paciente}/ficha-medica`**: Registra la ficha médica permanente (datos estáticos). Solo puede existir una por paciente.
  * **Permiso**: `hce:ficha-medica:write`
  * **Body (`FichaMedicaCreate`)**:
    ```json
    {
      "grupo_sanguineo": "A+",          // Opcional (Max. 10 caracteres)
      "peso_kg": 72.5,                  // Opcional (float, ej: 72.5)
      "altura_cm": 175.0,               // Opcional (float, ej: 175.0)
      "observaciones_generales": "string" // Opcional
    }
    ```

* **`PATCH /api/v1/pacientes/{id_paciente}/ficha-medica`**: Actualiza parcialmente los datos estáticos de la ficha.
  * **Permiso**: `hce:ficha-medica:write`
  * **Body (`FichaMedicaUpdate`)** (todos los campos opcionales):
    ```json
    {
      "grupo_sanguineo": "A-",
      "peso_kg": 70.0,
      "altura_cm": 175.0,
      "observaciones_generales": "string"
    }
    ```

* **`GET /api/v1/pacientes/{id_paciente}/alertas`**: Lista las alertas clínicas (activas e inactivas) del paciente.
  * **Permiso**: `hce:alertas:read`

* **`POST /api/v1/pacientes/{id_paciente}/alertas`**: Registra una nueva alerta de seguridad clínica.
  * **Permiso**: `hce:alertas:write`
  * **Body (`AlertaCreate`)**:
    ```json
    {
      "tipo": "alergia",                // Requerido. Enum: "alergia", "contraindicacion", "patologia_critica", "otra"
      "severidad": "alta",              // Requerido. Enum: "leve", "moderada", "alta"
      "descripcion": "string"           // Requerido (Ej: "Alergia severa a penicilina.")
    }
    ```

* **`PATCH /api/v1/pacientes/{id_paciente}/alertas/{id_alerta}`**: Resuelve/desactiva una alerta clínica activa.
  * **Permiso**: `hce:alertas:write`
  * **Body (`AlertaUpdate`)**:
    ```json
    {
      "estado": "resuelta",             // Requerido. Enum: "activa", "resuelta"
      "motivo_resolucion": "string"     // Requerido (Ej: "Confirmado negativo por test de provocación.")
    }
    ```

* **`GET /api/v1/pacientes/{id_paciente}/antecedentes`**: Lista los antecedentes del historial de salud.
  * **Permiso**: `hce:antecedentes:read`

* **`POST /api/v1/pacientes/{id_paciente}/antecedentes`**: Agrega un antecedente médico.
  * **Permiso**: `hce:antecedentes:write`
  * **Body (`AntecedenteCreate`)**:
    ```json
    {
      "tipo": "quirurgico",             // Requerido. Enum: "patologico", "quirurgico", "familiar", "habito", "otro"
      "descripcion": "string",          // Requerido (Ej: "Colecistectomía laparoscópica")
      "fecha_suceso": "2018-04-15",     // Opcional (Date, YYYY-MM-DD)
      "observaciones": "string"         // Opcional
    }
    ```

* **`PATCH /api/v1/pacientes/{id_paciente}/antecedentes/{id_antecedente}`**: Actualiza un antecedente existente.
  * **Permiso**: `hce:antecedentes:write`
  * **Body (`AntecedenteUpdate`)** (todos los campos opcionales):
    ```json
    {
      "descripcion": "string",
      "fecha_suceso": "2018-04-15",
      "observaciones": "string"
    }
    ```

---

### 5.3 Módulos de Integración Externa

* **Integración M3 - Farmacia (`/recetas`)**
  * **`GET /api/v1/recetas`**: Obtiene recetas generadas. Soporta filtros opcionales de query: `id_paciente`, `estado` ("activa", "archivada", "cancelada") y `desde_fecha`.
    * **Permiso**: `hce:recetas:read`
  * **`GET /api/v1/recetas/{id_receta}`**: Obtiene detalles de una receta, incluyendo su **Smart Payload** con alertas activas del paciente.
    * **Permiso**: `hce:recetas:read`

* **Integración M4/M5 - Estudios (`/ordenes` y `/resultados`)**
  * **`GET /api/v1/ordenes`**: Obtiene órdenes pendientes. Reclama Query Param `tipo_estudio` ("Laboratorio", "Imagen").
    * **Permiso**: `hce:ordenes:read`
  * **`GET /api/v1/ordenes/{id_orden}`**: Detalle de orden con Smart Payload de alertas.
    * **Permiso**: `hce:ordenes:read`
  * **`POST /api/v1/resultados`**: Registra el informe final del estudio finalizado.
    * **Permiso**: `hce:resultados:write`
    * **Body (`ResultadoEstudioRequest`)**:
      ```json
      {
        "id_orden": 4050,               // Opcional. ID de la orden originaria.
        "id_paciente": 10500,           // Requerido.
        "tipo_estudio": "Imagen",        // Requerido. Enum: "Laboratorio", "Imagen", "Cardiologia", "Otro"
        "id_profesional_firmante": "str",// Requerido. Nombre/ID del médico que firma.
        "fecha_resultado": "2026-06-04T19:54:00Z", // Requerido. DateTime ISO.
        "informe_resumen": "string",    // Opcional. Informe en formato texto.
        "id_externo_estudio": "string"  // Opcional. Referencia PACS/LIS externa.
      }
      ```

* **Integración M6 - Camas/Internación (`/internacion`)**
  * **`POST /api/v1/internacion/ingreso`**: Notifica el ingreso físico del paciente a una cama. Crea automáticamente el `Episodio` de internación y su primer `MovimientoInternacion`.
    * **Permiso**: `hce:internacion:write`
    * **Body (`IngresoInternacionRequest`)**:
      ```json
      {
        "id_paciente": 10500,           // Requerido.
        "sector": "UTI",                // Requerido (Ej: "UTI", "Guardia").
        "habitacion": "Terapia A",      // Opcional.
        "cama": "Cama 4",               // Requerido.
        "fecha_ingreso": "2026-06-04T19:54:00Z", // Requerido.
        "medico_solicitante": "string"  // Opcional.
      }
      ```

* **Integración M7 - Coberturas (`/patients/{id_paciente}/insurance`)**
  * **`GET /api/v1/patients/{id_paciente}/insurance`**: Obtiene la obra social/prepaga del paciente para que Facturación aplique nomencladores.
    * **Permiso**: `hce:insurance:read`

* **Integración M10 - Core (`/hce/notify-permission-change`)**
  * **`POST /api/v1/hce/notify-permission-change`**: Reenvía a Core una notificación de cambio de permisos originada en HCE.
    * **Permiso**: `hce:write`
    * **Body (`PermissionChangeNotification`)**:
      ```json
      {
        "id_usuario_afectado": 42,       // Requerido. ID del médico.
        "tipo_cambio": "revoke-access",  // Requerido. Enum: "grant-access", "revoke-access"
        "recurso_afectado": "hce:write", // Opcional. Recurso de permiso afectado.
        "motivo": "string",              // Requerido. Motivo del cambio.
        "id_usuario_notificador": 10,    // Opcional.
        "fecha_ocurrencia": "2026-06-04T19:54:00Z" // Opcional.
      }
      ```

---

## 6. Desarrollo y Testing Local

Para correr las pruebas e inicializar la base de datos de test local (`test.db`):
```bash
# Activar entorno virtual
.\venv\Scripts\activate

# Correr tests unitarios
pytest
```
*Las pruebas limpian y recrean todas las tablas utilizando `Base.metadata.create_all` y `drop_all` antes y después de cada test de forma aislada ([tests/conftest.py](file:///c:/Users/monti/Desktop/Desarrollo_de_apps_ii/healthgrid-hce-backend/hce-backend/tests/conftest.py#L34)).*
