# Guía de Integración Frontend-Backend — Módulo HCE (Historia Clínica Electrónica)

Esta guía detalla la arquitectura, endpoints clave, estructura de autenticación y estrategia de transición (Mock vs Real) para conectar la aplicación Frontend con el Backend de HCE.

---

## ⚙️ 1. Estrategia de Transición: Mock vs Real (Environment Variables)

Para permitir a los desarrolladores y agentes de IA alternar dinámicamente entre mocks locales y el backend real, implementaremos un sistema de abstracción mediante variables de entorno y el patrón Service Factory.

### Variables de Entorno (`.env.local` / `.env.development`)
```bash
# Define si el frontend usa datos locales mockeados (true) o llamadas reales de red (false)
VITE_USE_MOCKS=true

# URL base del API de HCE
VITE_API_URL=http://localhost:8001/api/v1
```

### Arquitectura de Capas de Servicio
Para desacoplar las vistas/componentes del origen de datos, se estructuran los servicios de la siguiente forma:

1. **`types.ts`**: Definición de interfaces TypeScript basadas en las respuestas JSON del backend.
2. **`api/`**: Contiene la implementación HTTP real utilizando `fetch` o `axios` apuntando a `VITE_API_URL`.
3. **`mocks/`**: Contiene la simulación local utilizando datos harcodeados o almacenamiento temporal local.
4. **`ServiceFactory`**: Determina qué clase instanciar según el valor de `VITE_USE_MOCKS`.

#### Ejemplo de Implementación (`src/services/salaEsperaService.ts`):
```typescript
import { SalaEsperaSchema, SalaEsperaPrioridad } from './types';
import { SalaEsperaApi } from './api/SalaEsperaApi';
import { SalaEsperaMock } from './mocks/SalaEsperaMock';

export interface ISalaEsperaService {
  listar(medicoId?: number, sedeId?: number): Promise<SalaEsperaSchema[]>;
  ingresar(pacienteId: number, medicoId: number, sedeId: number): Promise<SalaEsperaSchema>;
  actualizarPrioridad(idEspera: number, prioridad: number, motivo?: string): Promise<SalaEsperaSchema>;
  llamar(idEspera: number, consultorio: number): Promise<SalaEsperaSchema>;
  atender(idEspera: number, idEpisodio?: number): Promise<SalaEsperaSchema>;
}

const useMocks = import.meta.env.VITE_USE_MOCKS === 'true';

export const SalaEsperaService: ISalaEsperaService = useMocks
  ? new SalaEsperaMock()
  : new SalaEsperaApi();
```

---

## 🔑 2. Autenticación y Autorización (JWT)

El backend de HCE valida tokens JWT emitidos por el **Módulo 10 (Core)** de forma local. 
- Las peticiones HTTP reales deben adjuntar el header: `Authorization: Bearer <JWT_TOKEN>`.
- Las pantallas que consulten o escriban en HCE deben validar localmente o interceptar errores `401 Unauthorized` / `403 Forbidden` si los permisos del profesional de la salud no son adecuados.

---

## 🔌 3. Endpoints Clave y Mapeo de Objetos

El backend expone su documentación Swagger interactiva en `http://localhost:8001/docs`. Los flujos prioritarios a integrar son:

### A. Sala de Espera (Triage / Guardia / Consulta)

#### 1. Listar Pacientes
- **Método**: `GET`
- **Ruta**: `/api/v1/sala-espera`
- **Query Params**: `id_medico`, `id_sede`, `estado`, `ordenar_por` (`llegada` o `prioridad`).
- **Respuesta (`SalaEsperaSchema`)**:
  ```json
  [
    {
      "id_espera": 12,
      "id_paciente": 3002,
      "id_episodio": null,
      "id_medico": 42,
      "id_sede": 3,
      "id_turno_m2": 50002,
      "fecha_llegada": "2026-06-21T09:45:00Z",
      "fecha_turno": "2026-06-21T10:00:00Z",
      "prioridad": 1,
      "estado": "Esperando",
      "consultorio": null,
      "motivo": "-"
    }
  ]
  ```

#### 2. Registrar Ingreso Manual (Webhook/Recepción)
- **Método**: `POST`
- **Ruta**: `/api/v1/sala-espera/ingreso`
- **Body (`SalaEsperaCreate`)**:
  *(Nota: El motivo de consulta no se envía al ingresar, se inicializa automáticamente en `"-"`)*
  ```json
  {
    "id_paciente": 3002,
    "id_medico": 42,
    "id_sede": 3,
    "id_turno_m2": 50002,
    "fecha_turno": "2026-06-21T10:00:00Z",
    "fecha_llegada": "2026-06-21T09:45:00Z"
  }
  ```

#### 3. Clasificar Prioridad y Motivo (Triage - M9)
- **Método**: `PATCH`
- **Ruta**: `/api/v1/sala-espera/{id_espera}/prioridad`
- **Body (`SalaEsperaPrioridad`)**:
  *(El campo `motivo` es opcional; si no se envía, no se sobrescribe el motivo actual)*
  ```json
  {
    "prioridad": 3,
    "motivo": "Dolor fuerte de cabeza"
  }
  ```

#### 4. Llamar Paciente a Consultorio
- **Método**: `PATCH`
- **Ruta**: `/api/v1/sala-espera/{id_espera}/llamar`
- **Body (`SalaEsperaLlamar`)**:
  ```json
  {
    "consultorio": 104
  }
  ```

#### 5. Atender Paciente (Vinculación / Creación de Episodio)
- **Método**: `PATCH`
- **Ruta**: `/api/v1/sala-espera/{id_espera}/atender`
- **Body (`SalaEsperaAtender` - Opcional)**:
  ```json
  {
    "id_episodio": 123  // Enviar si se asocia a un episodio existente; omitir para crear uno automático
  }
  ```

---

### B. Historia Clínica, Ficha Médica y Pacientes

Para desplegar y persistir evoluciones clínicas, diagnósticos y recetas, así como consultar datos demográficos:

* **Consultar Datos de Paciente (Caché)**: `GET /api/v1/pacientes/{id_paciente}`
* **Listar Pacientes Cacheados**: `GET /api/v1/pacientes`
* **Ficha Médica del Paciente**: `GET /api/v1/pacientes/{id_paciente}/ficha-medica`
* **Listar Órdenes de un Paciente**: `GET /api/v1/pacientes/{id_paciente}/ordenes`
* **Agregar Antecedentes**: `POST /api/v1/pacientes/{id_paciente}/antecedentes`
* **Registrar Evolución**: `POST /api/v1/episodes/{id_episodio}/evoluciones`
* **Emitir Recetas**: `POST /api/v1/recetas`

---

## 🔑 3. Generación de Token JWT para Desarrollo

Cuando el frontend corre en modo real, el backend requiere autenticación por token Bearer en casi todos sus endpoints. Para facilitar el desarrollo y evitar depender del Módulo 10 (Core) levantado localmente, el backend de HCE incluye un endpoint especial de autenticación para desarrollo (activo únicamente si `APP_ENV` no es `production`).

### Endpoint de Login Dev
- **Método**: `POST`
- **Ruta**: `/api/v1/dev/login`
- **Body (`DevLoginRequest` - Opcional)**:
  Puedes enviar un cuerpo vacío `{}` para obtener un token con el usuario por defecto (médico con todos los permisos) o personalizarlo:
  ```json
  {
    "sub": 42,
    "username": "dr.triage",
    "role": "medico",
    "sede_id": 3,
    "permissions": [
      "hce:episodes:read",
      "hce:episodes:write"
    ]
  }
  ```
- **Respuesta (`DevLoginResponse`)**:
  Devuelve el token de acceso JWT y la información del usuario dev:
  ```json
  {
    "access_token": "ey...",
    "token_type": "bearer",
    "user": {
      "id": 42,
      "username": "dr.triage",
      "role": "medico",
      "permissions": ["hce:episodes:read", "hce:episodes:write"]
    }
  }
  ```

*Tip para el Agente Frontend:* Puedes configurar un script de inicio o una llamada en el setup del entorno de desarrollo del frontend para golpear este endpoint y almacenar automáticamente el token en `localStorage` o en los headers del cliente HTTP, lo que agilizará las pruebas manuales y automatizadas.

---

### C. Órdenes Médicas y Resultados de Estudios

Se ha reestructurado la lógica de órdenes y resultados médicos. La tabla genérica de resultados se ha dividido en dos tablas PostgreSQL específicas (`resultados_laboratorio` y `resultados_imagenes`) para mantener la coherencia clínica, y el endpoint de creación de órdenes se ha especializado por tipo.

#### 1. Crear Orden de Laboratorio (Módulo 4)
Este endpoint crea una orden vinculando un conjunto de IDs de estudios del catálogo bioquímico de M4.
- **Método**: `POST`
- **Ruta**: `/api/v1/pacientes/{id_paciente}/ordenes/laboratorio`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Body (`OrdenLaboratorioCreate`)**:
  ```json
  {
    "estudio_ids": [101, 102],
    "descripcion_pedido": "Muestras en ayunas de 8hs",
    "prioridad": "Normal", // "Normal", "Urgente", "Emergencia"
    "id_episodio": 12,     // Opcional
    "id_evolucion": 34     // Opcional
  }
  ```

#### 2. Crear Orden de Imágenes (Módulo 5)
Este endpoint crea una orden de imágenes indicando la modalidad específica (`subtipo`).
- **Método**: `POST`
- **Ruta**: `/api/v1/pacientes/{id_paciente}/ordenes/imagenes`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Body (`OrdenImagenCreate`)**:
  ```json
  {
    "subtipo": "RESONANCE", // Modulación/Subtipo
    "descripcion_pedido": "RM de cerebro con contraste. Descartar lesión.",
    "prioridad": "Urgente",
    "id_episodio": 12,     // Opcional
    "id_evolucion": 34     // Opcional
  }
  ```
  *(Nota: Los subtipos válidos para imágenes son: `ECOGRAFY`, `RADIOLOGY`, `TOMOGRAPHY`, `RESONANCE`, `MAMMOGRAPHY`, `DENSITOMETRY`, `ECODOPPLER`, `ENDOSCOPY`)*

> [!WARNING]
> El endpoint genérico anterior `POST /api/v1/pacientes/{id_paciente}/ordenes` ha sido marcado como **deprecated (obsoleto)**. Los formularios del frontend del médico deben migrarse para llamar a las rutas específicas detalladas arriba según corresponda.

#### 3. Consultar Historial de Resultados Unificados (M8 - Portal del Paciente)
Para listar todos los resultados médicos del paciente de forma cronológica, se debe consultar el siguiente endpoint unificado. HCE une en background los resultados de las dos tablas (`resultados_laboratorio` y `resultados_imagenes`) ordenándolos por fecha descendente.
- **Método**: `GET`
- **Ruta**: `/api/v1/patients/{id_paciente}/historial-resultados`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Respuesta (`List[ResultadoEstudioResumen]`)**:
  ```json
  [
    {
      "id_resultado": 1,
      "id_orden": 105,
      "tipo_estudio": "Laboratorio",
      "fecha_resultado": "2026-06-25T14:30:00Z",
      "titulo": "Resultado de Análisis de Laboratorio",
      "resumen": "Análisis de glucemia y colesterol",
      "profesional_firmante": "Dra. García (Bioquímica)",
      "subtipo": null,
      "link_imagen": null,
      "url_detalle": null,
      "analitos": [
        {
          "nombre": "Glucosa",
          "valor": 95.0,
          "unidad": "mg/dL",
          "rango_normal": { "min": 70.0, "max": 110.0 },
          "fuera_de_rango": false,
          "es_critico": false,
          "observacion": "En ayunas"
        },
        {
          "nombre": "Colesterol Total",
          "valor": 240.0,
          "unidad": "mg/dL",
          "rango_normal": { "min": 120.0, "max": 200.0 },
          "fuera_de_rango": true,
          "es_critico": false,
          "observacion": "Levemente elevado"
        }
      ],
      "resumen_analitos": {
        "total_analitos": 2,
        "analitos_fuera_de_rango": 1,
        "hay_valores_criticos": false
      }
    },
    {
      "id_resultado": 4,
      "id_orden": 106,
      "tipo_estudio": "Imagen",
      "fecha_resultado": "2026-06-25T15:00:00Z",
      "titulo": "Resonancia Magnética de Cerebro con Contraste",
      "resumen": "Se observa tejido cerebral normal...",
      "profesional_firmante": "Dr. Nicolas Garcia (Radiólogo)",
      "subtipo": "RESONANCE",
      "link_imagen": "https://viewer.pacs.hospital/study/RPT-M5-999",
      "url_detalle": "https://api.imagenes.hospital/v1/estudios/106/completo",
      "analitos": null,
      "resumen_analitos": null
    }
  ]
  ```

#### 4. Consultar Órdenes del Paciente (Para Portal / Ficha Médica)
Para obtener todas las órdenes de estudio (tanto de imágenes como de laboratorio) solicitadas para un paciente y conocer su estado actual, prioridad y datos clínicos:
- **Método**: `GET`
- **Ruta**: `/api/v1/pacientes/{id_paciente}/ordenes`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>`
- **Respuesta (`OrdenListResponse`)**:
  ```json
  {
    "status": "success",
    "cantidad": 1,
    "data": [
      {
        "id_orden": 105,
        "id_paciente": 10500,
        "tipo_estudio": "Imagen",
        "descripcion_pedido": "RM de cerebro con contraste. Descartar lesión.",
        "prioridad": "Urgente",
        "id_episodio": 12,
        "id_evolucion": 34,
        "fecha_creacion": "2026-06-25T14:30:00Z",
        "id_medico_solicitante": 42,
        "subtipo": "RESONANCE",
        "estudio_ids": null,
        "estado": "Pendiente",
        "alertas_clinicas": []
      }
    ]
  }
  ```

#### 5. Consultar Resultado de una Orden Específica (Por ID de Orden)
Si deseas consultar el resultado clínico exacto asociado a una orden médica conociendo su ID y su tipo de estudio:
- **Método**: `GET`
- **Ruta**: `/api/v1/ordenes/{id_orden}/resultado?tipo_estudio=<Laboratorio|Imagen>`
- **Headers**: `Authorization: Bearer <JWT_TOKEN>` (Permiso: `hce:resultados:read`)
- **Respuesta (`ResultadoEstudioResumen`)**:
  ```json
  {
    "id_resultado": 42,
    "id_orden": 106,
    "tipo_estudio": "Imagen",
    "fecha_resultado": "2026-06-25T15:00:00Z",
    "titulo": "Resonancia Magnética de Cerebro con Contraste",
    "resumen": "Se observa tejido cerebral normal...",
    "profesional_firmante": "Dr. Nicolas Garcia (Radiólogo)",
    "subtipo": "RESONANCE",
    "link_imagen": "https://viewer.pacs.hospital/study/RPT-M5-999",
    "url_detalle": "https://api.imagenes.hospital/v1/estudios/106/completo",
    "analitos": null,
    "resumen_analitos": null
  }
  ```

---

## 🚀 4. Plan de Acción Recomendado para el Agente Frontend

1. **Crear Rama de Trabajo**: `feature/integrate-hce-backend`.
2. **Configurar Variable**: Añadir `VITE_USE_MOCKS=true` in `.env.local`.
3. **Modelar Interfaces**:
   * Generar tipos TypeScript para `OrdenLaboratorioCreate`, `OrdenImagenCreate`, `OrdenListResponse`, y la respuesta unificada `ResultadoEstudioResumen` detalladas en esta guía.
4. **Actualizar Formularios de Prescripción (Médico)**:
   * **Sección Laboratorio**: Reemplazar la llamada vieja por `/api/v1/pacientes/{id_paciente}/ordenes/laboratorio`, permitiendo seleccionar estudios del catálogo y enviando el array `estudio_ids`.
   * **Sección Imágenes**: Reemplazar la llamada por `/api/v1/pacientes/{id_paciente}/ordenes/imagenes`, permitiendo elegir la modalidad (ej. "Radiología", "Resonancia") y enviando el string en `subtipo`.
5. **Actualizar Visualización en el Portal del Paciente**:
   * Implementar lógica condicional al listar el historial:
     * Si `tipo_estudio === "Imagen"`, mostrar botón para **"Ver placa DICOM / PACS"** apuntando a `link_imagen`.
     * Si `tipo_estudio === "Laboratorio"`, renderizar una tabla interactiva con la lista de `analitos`, resaltando visualmente en rojo aquellos cuyo campo `fuera_de_rango` sea `true` o `es_critico` sea `true`.
6. **Implementar Factory Pattern**: Migrar los componentes del frontend para que consuman servicios estructurados (`ISalaEsperaService`).
7. **Validar Localmente**: Asegurar que con `VITE_USE_MOCKS=true` la app sigue funcionando al 100% como antes.
8. **Configurar Login de Dev**: Si se detecta `VITE_USE_MOCKS=false` y no hay un token guardado, invocar `POST /api/v1/dev/login` para simular la sesión.
9. **Probar Modo Real**: Levantar el backend de HCE en `localhost:8001`, realizar ingresos y triages reales, y verificar persistencia.
