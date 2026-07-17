# Tutorial: Comunicacion entre microservicios

Esta guia va al grano: como conectar microservicios usando el Core como punto de configuracion y publicacion.

La idea, cortita y al pie ( • ̀ω•́ )✧:

- Las colas se crean desde el Core.
- Los eventos se crean desde el Core.
- Los bindings entre eventos y colas se hacen desde el Core.
- Los microservicios escuchan sus propias colas de respuesta en RabbitMQ.
- Los microservicios publican mensajes llamando al Core.

Regla mental: RabbitMQ para escuchar; Core para configurar y publicar. Asi evitamos colas creadas a mano y bindings fantasma. ദ്ദി ˉ͈̀꒳ˉ͈́ )✧

## Conceptos

### Requests

Una `request` es un pedido que un microservicio le manda a otro.

Ejemplo:

`appointments` le pide a `billing` que cree una factura.

### Responses

Una `response` es la respuesta a una request anterior.

Ejemplo:

`billing` le responde a `appointments` que la factura fue creada.

### Correlation ID

Si una request espera respuesta, agreguen un `correlation_id`.

La response tiene que devolver ese mismo `correlation_id`.

Sirve para que quien hizo la request pueda saber a que pedido corresponde la respuesta. 

Ejemplo de request:

```json
{
  "correlation_id": "9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45",
  "patient_id": 123,
  "appointment_id": 987
}
```

## Grafico del flujo

```mermaid
sequenceDiagram
    participant A as Appointments
    participant Core as Core API
    participant Rabbit as RabbitMQ
    participant B as Billing

    A->>Core: Crea cola appointments.responses
    A->>Core: Crea evento de response
    B->>Core: Crea cola billing.requests
    B->>Core: Crea evento de request
    A->>B: Comparte response_event_id
    B->>A: Comparte request_event_id
    A->>Core: POST /events/log request + correlation_id + response_event_id
    Core->>Rabbit: Publica request en health_grid_exchange
    Rabbit->>B: Entrega mensaje en billing.requests
    B->>B: Procesa request
    B->>Core: POST /events/log response + mismo correlation_id
    Core->>Rabbit: Publica response
    Rabbit->>A: Entrega mensaje en appointments.responses
    A->>A: Relaciona response usando correlation_id
```

## 1. Configurar cliente RabbitMQ ₍ ᐢ.ˬ.ᐢ₎

Cada microservicio recibe credenciales RabbitMQ con permisos limitados.

Ejemplo:

```text
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=admin@admin.com
RABBITMQ_PASSWORD=123123
RABBITMQ_VHOST=/
```

Si arman una URL AMQP, el `@` del email tiene que ir escapado como `%40`:

```text
amqp://admin%40admin.com:123123@localhost:5672/
```

El microservicio usa RabbitMQ solo para escuchar sus colas.

## 2. Login en el Core

Todos los endpoints del Core usan JWT.

Primero obtener token:

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@mail.com",
  "password": "1234"
}
```

Usar el token devuelto:

```http
Authorization: Bearer <token>
```

## 3. Crear colas desde el Core 

Endpoint:

```http
POST /rabbit/queues
Authorization: Bearer <token>
Content-Type: application/json
```

El Core agrega automaticamente el sufijo:

- `requests` crea `<queue_name>.requests`
- `responses` crea `<queue_name>.responses`

Tambien crea la DLQ:

- `<queue_name>.requests.dlq`
- `<queue_name>.responses.dlq`

### Si el microservicio recibe requests

Crear una cola de requests:

```json
{
  "queue_name": "billing",
  "queue_type": "requests"
}
```

Resultado:

```json
{
  "queue_name": "billing.requests",
  "queue_type": "requests",
  "dlq_name": "billing.requests.dlq",
  "rabbit_username": "user@mail.com"
}
```

### Si el microservicio espera responses

Crear una cola de responses:

```json
{
  "queue_name": "appointments",
  "queue_type": "responses"
}
```

Resultado:

```json
{
  "queue_name": "appointments.responses",
  "queue_type": "responses",
  "dlq_name": "appointments.responses.dlq",
  "rabbit_username": "user@mail.com"
}
```

## 4. Crear eventos desde el Core

Endpoint:

```http
POST /events/types
Authorization: Bearer <token>
Content-Type: application/json
```

### Evento para requests

Crear este evento si otros microservicios tienen que mandarle requests a tu servicio.

Este evento lo crea el microservicio que recibe la request.

Ejemplo: `billing` recibe pedidos para crear facturas, entonces `billing` crea:

```json
{
  "name": "billing.invoice.create.requested",
  "description": "Request para que billing cree una factura",
  "source_module": "billing"
}
```

Guardar el `id` devuelto. Ese es el `event_type_id` que otros microservicios usaran para pedirle cosas a `billing`.

### Evento para responses

Crear este evento si tu servicio hizo una request y necesita recibir una response.

Ejemplo: `appointments` le pide a `billing` que cree una factura y quiere recibir respuesta. Entonces `appointments` crea:

```json
{
  "name": "billing.invoice.create.responded",
  "description": "Response de billing para la creacion de factura",
  "source_module": "appointments"
}
```

Guardar el `id` devuelto. Ese ID se comparte con `billing` y tambien viaja en la request como `response_event_id`.

Mini resumen:

```text
Recibo requests: creo el evento request.
Espero responses: creo el evento response.
Proceso requests: NO creo el evento response; uso el response_event_id recibido.
```

## 5. Vincular eventos con colas

Endpoint:

```http
POST /rabbit/bindings
Authorization: Bearer <token>
Content-Type: application/json
```

### Bind de requests

Si `billing` recibe requests, bindear el evento request con la cola `billing.requests`:

```json
{
  "event_id": 10,
  "queue_name": "billing.requests"
}
```

Desde ese momento, todo mensaje publicado al evento `10` llega a `billing.requests`.

### Bind de responses

Si `appointments` espera responses, bindear el evento response con la cola `appointments.responses`:

```json
{
  "event_id": 11,
  "queue_name": "appointments.responses"
}
```

Desde ese momento, toda respuesta publicada al evento `11` llega a `appointments.responses`.

## 6. Escuchar una cola

El microservicio escucha su cola directamente en RabbitMQ.

Ejemplo conceptual:

```text
Conectar a RabbitMQ
Abrir canal
Consumir cola: appointments.responses
Por cada mensaje:
  1. Parsear mensaje externo del Core
  2. Parsear campo payload
  3. Leer correlation_id
  4. Procesar
  5. ACK
```

El mensaje que llega por Rabbit tiene este formato externo:

```json
{
  "event_type_id": 11,
  "event_type_name": "billing.invoice.create.responded",
  "source_module": "appointments",
  "publisher_module": "billing",
  "log_id": 456,
  "payload": "{\"correlation_id\":\"9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45\",\"status\":\"created\",\"invoice_id\":321}",
  "published_at": "2026-07-03T12:00:00Z"
}
```

Ojo tecnico: `payload` llega como string. Primero parsean el mensaje externo y despues ese JSON interno.

## 7. Definir payloads por evento

Cada evento necesita un contrato claro.

Ese contrato lo definen y lo comparten los equipos duenos del flujo.

### Payload de request

Ejemplo para `billing.invoice.create.requested`:

```json
{
  "correlation_id": "9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45",
  "appointment_id": 987,
  "patient_id": 123,
  "amount": 15000,
  "currency": "ARS",
  "response_event_id": 11
}
```

Campos recomendados:

- `correlation_id`: obligatorio si se espera respuesta.
- `response_event_id`: evento donde se publica la respuesta. Este ID lo define y lo comparte quien espera recibir la response.
- Datos de negocio necesarios para procesar la request.

### Payload de response

El payload de response lo acuerdan los microservicios del flujo.

Regla practica:

- Quien espera la response crea el evento de response.
- Quien procesa la request publica esa response usando el `response_event_id` recibido.

Ejemplo para `billing.invoice.create.responded`:

```json
{
  "correlation_id": "9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45",
  "status": "created",
  "invoice_id": 321,
  "error": null
}
```

Reglas:

- Usar el mismo `correlation_id` recibido en la request.
- Publicar al `event_type_id` recibido como `response_event_id`.
- Incluir `status`.
- Si falla, incluir informacion simple de error.

Ejemplo de error:

```json
{
  "correlation_id": "9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45",
  "status": "failed",
  "invoice_id": null,
  "error": {
    "code": "INVALID_AMOUNT",
    "message": "El monto debe ser mayor a cero"
  }
}
```

## 8. Que comparte cada microservicio

### Si tu microservicio recibe requests

Compartir con los demas equipos:

- ID del evento de request.
- Nombre del evento de request.
- Payload que tienen que enviarte.
- Payload de response.

No tenes que crear ni compartir el evento de response.

Ese evento lo crea quien hizo la request y espera recibir la respuesta.

Si tu microservicio va a responder, lee el `response_event_id` del payload de la request (o solicitalo al microservicio emisor) y publica ahi la response.

Ejemplo:

```text
Microservicio: billing
Request event id: 10
Request event name: billing.invoice.create.requested
Request payload: ver contrato billing.invoice.create.requested
```

### Si tu microservicio espera responses

Compartir con el servicio que va a responder:

- ID del evento de responses.
- Nombre del evento de responses.

Este ID tambien viaja en la request como `response_event_id`.

Ejemplo:

```text
Microservicio: appointments
Response event id: 11
Response event name: billing.invoice.create.responded
Response queue: appointments.responses
Response payload: ver contrato billing.invoice.create.responded
```

Resumen mini:

```text
Recibo requests: comparto mi event_id.
Espero responses: comparto mi event_id.
Proceso requests: respondo al response_event_id que me mandaron.
```

## 9. Publicar mensajes al Core

Los microservicios publican llamando al Core.

Endpoint:

```http
POST /events/log
Authorization: Bearer <token>
Content-Type: application/json
```

Body base:

```json
{
  "event_type_id": 10,
  "publisher_module": "appointments",
  "payload": "{\"correlation_id\":\"9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45\"}"
}
```

Ojo tecnico: `payload` va como string.

### Publicar una request

La request incluye el `response_event_id` si se espera respuesta.

Ese `response_event_id` lo creo el microservicio solicitante.

```json
{
  "event_type_id": 10,
  "publisher_module": "appointments",
  "payload": "{\"correlation_id\":\"9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45\",\"appointment_id\":987,\"patient_id\":123,\"amount\":15000,\"currency\":\"ARS\",\"response_event_id\":11}"
}
```

Si el evento `10` esta bindeado a `billing.requests`, `billing` recibe la request.

### Publicar una response

La response se publica al `event_type_id` que llego como `response_event_id` en la request.

El `correlation_id` tiene que ser el mismo.

```json
{
  "event_type_id": 11,
  "publisher_module": "billing",
  "payload": "{\"correlation_id\":\"9b9cfd23-8cc4-4ec3-a6e8-6d83f8f73b45\",\"status\":\"created\",\"invoice_id\":321,\"error\":null}"
}
```

Si el evento `11` esta bindeado a `appointments.responses`, `appointments` recibe la response.

## 10. Checklist rapido

Para recibir requests:

- Tener credenciales RabbitMQ.
- Crear cola `<servicio>.requests`.
- Crear evento de request.
- Bindear evento de request con `<servicio>.requests`.
- Escuchar `<servicio>.requests`.
- Compartir request event id, payload esperado y payload de respuesta si corresponde.

Para esperar responses:

- Tener credenciales RabbitMQ.
- Crear cola `<servicio>.responses`.
- Crear evento de response.
- Bindear evento de response con `<servicio>.responses`.
- Escuchar `<servicio>.responses`.
- Compartir `response_event_id` con el servicio que va a responder.
- Enviar ese ID en la request como `response_event_id`.

Para publicar:

- Generar `correlation_id` si se espera respuesta (random UUID).
- Armar payload segun contrato del evento.
- Enviar `POST /events/log` al Core.

## 11. Errores comunes ༼;´༎ຶ ۝ ༎ຶ༽

### No llega ningun mensaje

Checklist rapido para debuggear:

- La cola existe.
- El evento existe.
- El evento esta bindeado a la cola correcta.
- El microservicio escucha la cola con el sufijo correcto.
- El mensaje se publico con el `event_type_id` correcto.

### El responder publico a un evento incorrecto

Checklist rapido para debuggear:

- La request incluia `response_event_id`.
- El responder publico la response usando ese `response_event_id`.
- El evento de response fue creado y bindeado por quien espera la response.

### No se puede relacionar una response con una request

Checklist rapido para debuggear:

- La request tenia `correlation_id`.
- La response copio exactamente el mismo `correlation_id`.

### El payload llega como texto

Esto es normal: el mensaje externo trae `payload` como string.

Primero parseen el mensaje externo y despues parseen `payload`.

## 12. Resumen final: que tiene que hacer cada uno (❀ˆᴗˆ)(•́ᴗ•̀✿)

Si tu microservicio recibe requests:

- Pedir credenciales RabbitMQ al equipo del Core.
- Crear desde el Core una cola tipo `requests`, por ejemplo `billing.requests`.
- Crear desde el Core el evento de request, por ejemplo `billing.invoice.create.requested`.
- Vincular ese evento con tu cola `requests`.
- Escuchar tu cola en RabbitMQ con las credenciales recibidas.
- Definir y compartir el payload que esperas recibir y que pretendes devolver.
- Compartir con los demas equipos el `request_event_id`.
- Si vas a responder, leer de la request el `response_event_id` y publicar la response ahi.

Si tu microservicio hace requests y espera responses:

- Pedir credenciales RabbitMQ al equipo del Core.
- Crear desde el Core una cola tipo `responses`, por ejemplo `appointments.responses`.
- Crear desde el Core el evento de response, por ejemplo `billing.invoice.create.responded`.
- Vincular ese evento con tu cola `responses`.
- Escuchar tu cola de responses en RabbitMQ.
- Compartir el `response_event_id` con el microservicio que va a responder.
- Enviar en la request un `correlation_id` y el `response_event_id`.
- Cuando llegue la response, matchearla usando el mismo `correlation_id`.

Para publicar mensajes:

- Usar `POST /events/log` del Core.
- Mandar el `event_type_id` correcto.
- Enviar `payload` como string JSON.
- Incluir `correlation_id` si despues necesitas reconocer la response.

