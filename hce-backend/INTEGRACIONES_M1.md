# Integraciones — Módulo 1: HCE

> **Health Grid** · Desarrollo de Aplicaciones II · Ing. Joaquín Timerman
>
> Este documento explica, módulo por módulo, cómo se comunica el Módulo 1 (HCE) con el resto del sistema.
> Está pensado para que cualquier integrante del proyecto — sin importar el módulo en el que trabaje — pueda entender quién le habla a quién, qué datos se intercambian y por qué se eligió cada mecanismo de comunicación.

---

## ¿Qué es HCE y por qué todos se comunican con él?

El **Módulo 1 — Historia Clínica Electrónica (HCE)** es el repositorio central de datos médicos del sistema Health Grid. Todo lo que le sucede clínicamente a un paciente queda registrado acá:

- Consultas y evoluciones médicas
- Recetas electrónicas
- Órdenes de laboratorio e imágenes
- Resultados de estudios
- Solicitudes de internación
- Alertas y antecedentes clínicos

Por eso, casi todos los módulos necesitan comunicarse con HCE en algún momento: algunos para **avisarnos** que algo pasó, otros para **consultarnos** datos que solo nosotros tenemos, y nosotros para **notificarles** eventos clínicos que les interesan.

---

## Tipos de comunicación que usamos

| Tipo | Protocolo | Cuándo se usa |
|------|-----------|---------------|
| **SYNC** | REST HTTP | Cuando necesitamos una respuesta inmediata (confirmación, datos, error) |
| **ASYNC** | AMQP — RabbitMQ | Cuando solo notificamos que algo pasó y no necesitamos esperar respuesta |

> El broker RabbitMQ es administrado por **M10 Core**. El exchange central se llama `healthgrid.events` (tipo `topic`, durable). HCE publica y consume mensajes a través de ese exchange usando la librería `aio-pika`.

---

## M2 — Turnos

### ¿Qué hace M2?
Gestiona la agenda médica y los turnos de los pacientes.

### Tipo de comunicación
```
M2 ──ASYNC──► HCE
```

### ¿Qué pasa exactamente?

1. El paciente llega a la recepción del hospital y se registra en M2
2. M2 publica un evento AMQP con routing key `clinica.turnos.presentismo`
3. HCE tiene una queue llamada `hce.presentismo` escuchando ese evento
4. HCE recibe el evento y automáticamente crea un registro en la tabla `sala_espera`
5. El paciente queda en estado `ESPERANDO` en la cola de atención del médico

### Datos que M2 nos envía

```json
{
  "id_paciente": 10500,
  "id_turno": 88,
  "id_profesional": "MP-4521",
  "fecha_hora_llegada": "2025-07-16T09:30:00"
}
```

### ¿Por qué ASYNC?
M2 no necesita que HCE le responda nada. Solo avisa "el paciente llegó" y sigue su flujo. HCE procesa el evento cuando puede.

---

## M3 — Farmacia

### ¿Qué hace M3?
Gestiona el stock de medicamentos y dispensa recetas electrónicas.

### Tipo de comunicación
```
HCE ──ASYNC──► M3
```

### ¿Qué pasa exactamente?

1. El médico atiende al paciente en HCE y escribe una evolución clínica
2. Dentro de esa evolución, emite una receta electrónica
3. HCE guarda la receta en su propia tabla `recetas`
4. HCE publica un evento AMQP con routing key `clinica.farmacia.receta_creada`
5. M3 recibe el evento, sabe que hay una receta nueva y la prepara para dispensar en el mostrador

### Datos que HCE envía a M3

```json
{
  "id_receta": 42,
  "id_paciente": 10500,
  "id_medico": 7,
  "id_episodio": 201,
  "medicamentos": [
    {
      "nombre": "Ibuprofeno 400mg",
      "cantidad": "20 comprimidos",
      "indicaciones": "1 cada 8 horas con comidas"
    }
  ]
}
```

### ¿Por qué HCE le envía a M3 y no al revés?
Porque HCE es donde el médico **crea** la receta. M3 es donde se **ejecuta** (se dispensa el medicamento al paciente). Sin esta notificación, la farmacia no sabría que existe una receta nueva.

### ¿Por qué ASYNC?
HCE no necesita que la farmacia le confirme nada al momento de crear la receta. La farmacia la procesa cuando el paciente se acerca al mostrador.

---

## M4 — Laboratorio

### ¿Qué hace M4?
Procesa órdenes de análisis clínicos (sangre, orina, cultivos, etc.) y devuelve los resultados al sistema.

### Tipo de comunicación
```
HCE ──SYNC──► M4     (enviar orden)
M4  ──SYNC──► HCE    (devolver resultado via webhook)
HCE ──ASYNC──► M4    (notificación complementaria via AMQP)
```

### ¿Qué pasa exactamente?

**Parte 1 — Solicitar un estudio:**

1. El médico indica un análisis de sangre desde HCE
2. HCE hace un `POST /v1/ordenes` directo a M4 y espera confirmación
3. M4 responde confirmando que recibió la orden (201 Created)
4. HCE también publica el evento AMQP `clinica.estudios.orden_creada` como notificación adicional

**Datos que HCE envía a M4 (REST):**
```json
{
  "id_paciente": 10500,
  "id_episodio": 201,
  "prioridad": "URGENTE",
  "estudios": ["hemograma", "glucosa", "urea", "creatinina"]
}
```

**Parte 2 — Recibir el resultado:**

1. El laboratorio procesa la muestra y carga el resultado en M4
2. M4 llama al webhook de HCE: `POST /api/v1/webhook/laboratorio/resultado`
3. HCE guarda el resultado en la tabla `resultados_laboratorio`
4. El resultado queda disponible para el médico y para el portal del paciente (M8)

**Datos que M4 nos envía:**
```json
{
  "id_orden": 305,
  "fecha": "2025-07-16T14:00:00",
  "resultados": [
    { "parametro": "Glucosa", "valor": 95, "unidad": "mg/dL", "referencia": "70-100" },
    { "parametro": "Hemoglobina", "valor": 13.5, "unidad": "g/dL", "referencia": "12-16" }
  ]
}
```

### ¿Por qué la orden es SYNC?
Necesitamos saber si M4 aceptó la orden o hubo un error (paciente inválido, estudio no disponible). Si M4 falla, el médico tiene que saberlo en el momento.

### ¿Por qué el resultado llega por webhook y no nosotros lo pedimos?
Porque el laboratorio puede tardar horas o días. En vez de que HCE pregunte "¿ya está listo?" cada cierto tiempo, M4 nos llama cuando el resultado está disponible. Esto se llama patrón **push** (el que tiene el dato lo empuja hacia quien lo necesita).

---

## M5 — Diagnóstico por Imágenes

### ¿Qué hace M5?
Gestiona pedidos de radiografías, ecografías, tomografías, resonancias y devuelve los informes radiológicos.

### Tipo de comunicación
```
HCE ──SYNC──► M5     (enviar orden)
M5  ──SYNC──► HCE    (devolver informe via webhook)
HCE ──ASYNC──► M5    (notificación complementaria via AMQP)
```

### ¿Qué pasa exactamente?

**Parte 1 — Solicitar un estudio:**

1. El médico indica una radiografía de tórax desde HCE
2. HCE hace un `POST /v1/webhook/orders` a M5 y espera confirmación
3. M5 responde confirmando que recibió la orden

**Datos que HCE envía a M5 (REST):**
```json
{
  "id_paciente": 10500,
  "id_episodio": 201,
  "tipo_estudio": "Diagnóstico por imágenes",
  "subtipo": "Radiografía de tórax",
  "modulo_origen": "modulo1_hce"
}
```

**Parte 2 — Recibir el informe:**

1. El radiólogo firma el informe en M5
2. M5 llama al webhook de HCE: `POST /api/v1/webhook/imagenes/resultado`
3. HCE guarda el informe en la tabla `resultados_imagenes`

**Datos que M5 nos envía:**
```json
{
  "reportId": "RPT-8821",
  "hallazgos": "Sin imágenes patológicas evidentes",
  "informe": "Campos pulmonares libres. Silueta cardíaca normal.",
  "link_imagen": "https://pacs.hospital.com/imagen/8821"
}
```

> La lógica es idéntica a M4. La diferencia está en el tipo de estudio y el formato del resultado (informe radiológico vs. valores analíticos).

---

## M6 — Camas / Internación

### ¿Qué hace M6?
Administra la disponibilidad de camas hospitalarias y los movimientos de internación (ingreso, pase de sector, egreso).

### Tipo de comunicación
```
HCE ──SYNC──► M6     (solicitar cama)
M6  ──SYNC──► HCE    (confirmar o rechazar asignación)
HCE ──ASYNC──► M6    (avisar que el episodio cerró / alta del paciente)
```

### ¿Qué pasa exactamente?

**Parte 1 — Internar a un paciente:**

1. El médico decide que el paciente necesita internación
2. HCE hace un `POST /M6/solicitudes-internacion` a M6 y espera respuesta
3. M6 registra la solicitud y busca una cama disponible en el sector indicado
4. Cuando M6 asigna (o rechaza) una cama, llama al callback de HCE: `POST /api/v1/internacion/callback`
5. HCE actualiza el estado de la solicitud en la tabla `solicitudes_cama`

**Datos que HCE envía a M6 (REST):**
```json
{
  "id_paciente": 10500,
  "id_episodio": 201,
  "prioridad": "URGENTE",
  "sector": "Clínica Médica",
  "diagnostico_principal": "Neumonía bacteriana"
}
```

**Datos que M6 nos devuelve (callback REST):**
```json
{
  "id_solicitud": 77,
  "estado": "APROBADA",
  "nro_cama": "12B",
  "habitacion": "304"
}
```

**Parte 2 — Alta del paciente:**

1. El médico da el alta al paciente y cierra el episodio en HCE
2. HCE publica el evento AMQP `clinica.hce.episodio_cerrado`
3. M6 recibe el evento y libera la cama automáticamente

**Datos que HCE publica al cerrar el episodio:**
```json
{
  "id_episodio": 201,
  "id_paciente": 10500,
  "diagnostico": "Neumonía bacteriana — alta por mejoría",
  "prestaciones": ["internación 5 días", "radiografía tórax", "hemograma"]
}
```

### ¿Por qué la solicitud de cama es SYNC?
El médico necesita saber si hay cama disponible para tomar decisiones inmediatas. Si M6 rechaza (no hay cama en Clínica Médica), el médico puede pedir otro sector en el momento.

### ¿Por qué el alta es ASYNC?
Cuando el médico da el alta, HCE no necesita que M6 confirme que liberó la cama para continuar su flujo. Solo avisa y M6 procesa cuando puede.

---

## M7 — Facturación

### ¿Qué hace M7?
Liquida las prestaciones médicas a las obras sociales y prepagas.

### Tipo de comunicación
```
HCE ──ASYNC──► M7    (avisar que el episodio cerró)
M7  ──SYNC──► HCE    (consultar cobertura y episodios para facturar)
```

### ¿Qué pasa exactamente?

1. HCE cierra un episodio (alta médica) y publica `clinica.hce.episodio_cerrado` por AMQP
2. M7 recibe el evento y sabe que hay prestaciones nuevas para liquidar
3. M7 consulta a HCE para obtener los datos que necesita para armar la factura:

**Cobertura médica** (`GET /api/v1/patients/{id}/insurance`):
```json
{
  "nombre_obra_social": "OSDE",
  "plan": "210",
  "nro_afiliado": "4-2156-8",
  "vigente_desde": "2023-01-01"
}
```

**Episodios del paciente** (`GET /api/v1/patients/{id}/episodes`):
```json
[
  {
    "id": 201,
    "tipo": "INTERNACION",
    "estado": "CERRADO",
    "fecha_apertura": "2025-07-10",
    "fecha_cierre": "2025-07-15",
    "diagnostico_principal": "Neumonía bacteriana"
  }
]
```

### ¿Por qué HCE no le manda todo a M7 directamente al cerrar el episodio?
Porque M7 factura en sus propios tiempos, que pueden ser días o semanas después del alta. HCE solo avisa que el episodio cerró, y M7 decide cuándo consultar los datos y emitir la liquidación.

---

## M8 — Portal del Paciente

### ¿Qué hace M8?
Es la aplicación donde el paciente puede ver su historial clínico desde el celular o la computadora (tipo "Mi Salud").

### Tipo de comunicación
```
M8  ──SYNC──► HCE    (consultar historial — solo lectura)
```

### ¿Qué pasa exactamente?

1. El paciente entra al portal y quiere ver sus recetas o resultados de estudios
2. M8 consulta a HCE usando el JWT del paciente autenticado
3. HCE devuelve el historial filtrado para ese paciente

**Recetas** (`GET /api/v1/pacientes/{id}/historial/recetas`):
```json
[
  {
    "id_receta": 42,
    "fecha": "2025-07-16",
    "medico": "Dr. García",
    "medicamentos": ["Ibuprofeno 400mg — 1 cada 8 horas"]
  }
]
```

**Resultados de estudios** (`GET /api/v1/pacientes/{id}/historial/resultados`):
```json
{
  "laboratorio": [
    { "fecha": "2025-07-16", "parametro": "Glucosa", "valor": 95, "unidad": "mg/dL" }
  ],
  "imagenes": [
    { "fecha": "2025-07-15", "tipo": "Rx Tórax", "informe": "Sin hallazgos patológicos" }
  ]
}
```

### Punto importante
**HCE es solo lectura para M8.** M8 nunca nos crea ni modifica datos, solo consulta el historial existente.

---

## M10 — Core

### ¿Qué hace M10?
Es el núcleo del sistema: gestiona usuarios, roles, permisos, opera el broker RabbitMQ y sirve como API Gateway.

### Tipo de comunicación
```
M10 ──SYNC──► HCE    (JWT en cada request — autenticación)
HCE ──SYNC──► M10    (registrar webhooks al arrancar)
HCE ──ASYNC──► M10   (notificar patología crítica)
```

### ¿Qué pasa exactamente?

**Canal 1 — Autenticación (el más frecuente):**

- Cada request que llega a HCE desde cualquier usuario trae un token JWT en el header `Authorization: Bearer`
- Ese token lo emitió M10 cuando el usuario hizo login
- HCE lo valida **localmente** usando la clave compartida `super-secret-key-compartida-con-core`
- No necesita llamar a M10 en cada request — la validación es local y muy rápida
- Si el token es válido, HCE extrae el rol y los permisos y decide si autoriza la operación

**Contenido del JWT:**
```json
{
  "sub": 7,
  "username": "dr.garcia",
  "role": "medico",
  "permissions": ["hce:read", "hce:write", "hce:ordenes:write", "hce:recetas:write"],
  "sedeId": 3,
  "iat": 1752700000,
  "exp": 1752786400
}
```

**Canal 2 — Registro de webhooks al arrancar:**

- Cuando HCE inicia, se suscribe ante Core para recibir notificaciones de M4 y M5
- Le dice: "cuando M4 tenga un resultado listo, mandámelo a esta URL"
- `POST /events/subscriptions`

```json
{
  "event_type_id": 5,
  "subscriber_module": "modulo1_hce",
  "endpoint_url": "http://localhost:8000/api/v1/webhook/laboratorio/resultado"
}
```

**Canal 3 — Patología crítica:**

- Si el médico diagnostica una enfermedad de notificación obligatoria (tuberculosis, dengue, meningitis, etc.)
- HCE publica `clinica.hce.patologia_critica_detectada` por AMQP
- Core recibe el evento y lo procesa (alertas epidemiológicas, notificaciones institucionales)

```json
{
  "id_paciente": 10500,
  "patologia": "Tuberculosis pulmonar",
  "nivel_criticidad": "ALTO"
}
```

---

## Resumen global

### ¿Quién le habla a quién?

```
M2  ──ASYNC──► HCE              Presentismo del paciente
HCE ──ASYNC──► M3               Receta médica creada
HCE ──SYNC───► M4               Solicitar orden de laboratorio
M4  ──SYNC───► HCE              Entregar resultado de laboratorio
HCE ──SYNC───► M5               Solicitar orden de imágenes
M5  ──SYNC───► HCE              Entregar informe de imágenes
HCE ──SYNC───► M6               Solicitar cama de internación
M6  ──SYNC───► HCE              Confirmar/rechazar asignación de cama
HCE ──ASYNC──► M6               Episodio cerrado (alta del paciente)
M7  ──SYNC───► HCE              Consultar cobertura y episodios para facturar
HCE ──ASYNC──► M7               Episodio cerrado (prestaciones listas para liquidar)
M8  ──SYNC───► HCE              Consultar historial del paciente (solo lectura)
M10 ──SYNC───► HCE              JWT en cada request (autenticación)
HCE ──SYNC───► M10              Registro de webhooks al arrancar
HCE ──ASYNC──► M10              Detección de patología crítica
```

### Tabla de todas las comunicaciones

| # | Desde | Hacia | Tipo | Mecanismo | Qué se intercambia |
|---|-------|-------|------|-----------|-------------------|
| 1 | M10 Core | HCE | SYNC | JWT HS256 | Identidad, rol y permisos del usuario |
| 2 | HCE | M10 Core | SYNC · REST | `POST /events/subscriptions` | Registro de URLs de webhook |
| 3 | M2 Turnos | HCE | ASYNC · AMQP | `clinica.turnos.presentismo` | id_paciente, id_turno, fecha_llegada |
| 4 | HCE | M3 Farmacia | ASYNC · AMQP | `clinica.farmacia.receta_creada` | Receta con medicamentos e indicaciones |
| 5 | HCE | M4 Laboratorio | SYNC · REST | `POST /v1/ordenes` | Estudios solicitados con prioridad |
| 6 | M4 Laboratorio | HCE | SYNC · REST | `POST /webhook/laboratorio/resultado` | Resultados con valores y rangos de referencia |
| 7 | HCE | M4 Laboratorio | ASYNC · AMQP | `clinica.estudios.orden_creada` | Notificación de orden creada (tipo: lab) |
| 8 | HCE | M5 Imágenes | SYNC · REST | `POST /v1/webhook/orders` | Tipo y subtipo de estudio solicitado |
| 9 | M5 Imágenes | HCE | SYNC · REST | `POST /webhook/imagenes/resultado` | Informe radiológico y link a la imagen |
| 10 | HCE | M5 Imágenes | ASYNC · AMQP | `clinica.estudios.orden_creada` | Notificación de orden creada (tipo: imagen) |
| 11 | HCE | M6 Camas | SYNC · REST | `POST /M6/solicitudes-internacion` | Paciente, episodio, prioridad, sector |
| 12 | M6 Camas | HCE | SYNC · REST | `POST /internacion/callback` | Estado de la solicitud y número de cama |
| 13 | HCE | M6 Camas | ASYNC · AMQP | `clinica.hce.episodio_cerrado` | Episodio cerrado con diagnóstico y prestaciones |
| 14 | M7 Facturación | HCE | SYNC · REST | `GET /patients/{id}/insurance` | Cobertura médica y plan del paciente |
| 15 | M7 Facturación | HCE | SYNC · REST | `GET /patients/{id}/episodes` | Episodios con diagnóstico y fechas |
| 16 | HCE | M7 Facturación | ASYNC · AMQP | `clinica.hce.episodio_cerrado` | Episodio cerrado con prestaciones para liquidar |
| 17 | M8 Portal | HCE | SYNC · REST | `GET /pacientes/{id}/historial/recetas` | Historial de recetas del paciente |
| 18 | M8 Portal | HCE | SYNC · REST | `GET /pacientes/{id}/historial/resultados` | Historial de estudios del paciente |
| 19 | HCE | M10 Core | ASYNC · AMQP | `clinica.hce.patologia_critica_detectada` | Patología, nivel de criticidad |

### Regla general para entender cuándo usamos cada tipo

| Si el módulo necesita... | Usamos |
|--------------------------|--------|
| Una respuesta inmediata (datos, confirmación, error) | **SYNC REST** |
| Solo avisar que algo pasó, sin esperar respuesta | **ASYNC AMQP** |
| Recibir un evento de otro módulo en tiempo real | **ASYNC AMQP** (queue dedicada) |
| Validar quién es el usuario | **SYNC JWT** (local, sin llamada a M10) |
