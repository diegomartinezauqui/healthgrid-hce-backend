# v1/webhook/notifications

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/webhook/notifications:
    post:
      summary: v1/webhook/notifications
      deprecated: false
      description: >-
        Recibe una notificacion sobre la disponibilidad de un nuevo elemento a
        sincronizar como una orden o un turno para poder ser solicitada al
        recurso correspondiente
      tags:
        - Webhooks
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                type:
                  type: string
                  x-apidog-mock: ORDER | SCHEDULE
                  description: Tipo de notificacion de referencia
                id:
                  type: string
                  x-apidog-mock: '{{$string.uuid}}'
                  description: ID del elemento a consultar
              x-apidog-orders:
                - type
                - id
              required:
                - type
                - id
            examples: {}
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
                x-apidog-orders: []
          headers: {}
          x-apidog-name: OK
        '400':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Código de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: Los parámetros ingresados son icorrectos o tienen faltantes.
                errorCode: '7'
          headers: {}
          x-apidog-name: Bad request
        '404':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                x-apidog-orders:
                  - message
                required:
                  - message
              example:
                message: La ruta solicitada no existe
                errorCode: '7'
          headers: {}
          x-apidog-name: Not Found
        '500':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Codigo de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: No se pudo recuperar la informacion del paciente
                errorCode: '7'
          headers: {}
          x-apidog-name: Internal server error
      security: []
      x-apidog-folder: Webhooks
      x-apidog-status: developing
      x-run-in-apidog: https://app.apidog.com/web/project/1259681/apis/api-36860964-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: https://uade-da2-backend.onrender.com
    description: Entorno producción
security: []

```
# v1/webhook/reports/patientResume

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/webhook/patients/patientResume:
    get:
      summary: v1/webhook/reports/patientResume
      deprecated: false
      description: >-
        Devuelve el detalle básico de los informes finalizados de un paciente y
        poder listarlo en el home del paciente
      tags:
        - Webhooks
      parameters:
        - name: patientId
          in: query
          description: UUID paciente
          required: false
          example: 1ec08923-b600-4868-8429-057c37bebd3d
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  patientId:
                    type: string
                    description: UUID del paciente
                    x-apidog-mock: '{{$string.uuid}}'
                  reports:
                    type: array
                    items:
                      type: object
                      properties:
                        reportId:
                          type: string
                          description: UUID del informe
                          x-apidog-mock: '{{$string.uuid}}'
                        title:
                          type: string
                          description: Titulo/nombre del estudio
                        date:
                          type: string
                          description: Fecha en la que se hizo
                        doctorName:
                          type: string
                          description: Nombre del doctor
                        type:
                          type: string
                      x-apidog-orders:
                        - reportId
                        - title
                        - date
                        - doctorName
                        - type
                      required:
                        - reportId
                        - title
                        - date
                        - doctorName
                        - type
                x-apidog-orders:
                  - patientId
                  - reports
                required:
                  - patientId
                  - reports
              example:
                patientId: 1ec08923-b600-4868-8429-057c37bebd3d
                reports:
                  - reportId: eb01da40-1a83-40b2-87d2-e5710d8ee4b8
                    title: Ecografía abdominal
                    date: '2025-08-06'
                    doctorName: Dr. Facundo Gomez
                    type: ECOGRAFY
                  - reportId: 6e0365e4-bc91-464d-9382-a578064f417b
                    title: TAC de espalda
                    date: '2025-08-06'
                    doctorName: Dr. Ignacio Antuain
                    type: RADIOLOGY
          headers: {}
          x-apidog-name: OK
        '400':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Código de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: Los parámetros ingresados son icorrectos o tienen faltantes.
                errorCode: '7'
          headers: {}
          x-apidog-name: Bad request
        '500':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Codigo de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: No se pudo recuperar la informacion del paciente
                errorCode: '7'
          headers: {}
          x-apidog-name: Internal server error
      security: []
      x-apidog-folder: Webhooks
      x-apidog-status: developing
      x-run-in-apidog: https://app.apidog.com/web/project/1259681/apis/api-33600700-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: https://uade-da2-backend.onrender.com
    description: Entorno producción
security: []

```
# v1/webhook/images/reportId

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/webhook/images/reportId:
    get:
      summary: v1/webhook/images/reportId
      deprecated: false
      description: Devuelve el listado de imágenes asociadas a un reporte específico
      tags:
        - Webhooks
      parameters:
        - name: reportId
          in: query
          description: UUID del informe
          required: false
          example: 7cc5a7f0-9510-4a71-a927-aaf14f1337de
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  reportId:
                    type: string
                    description: UUID del reporte
                    x-apidog-mock: '{{$string.uuid}}'
                  images:
                    type: array
                    items:
                      type: object
                      properties:
                        imageId:
                          type: string
                          description: Id de la imagen
                          x-apidog-mock: '{{$string.uuid}}'
                        creatorName:
                          type: string
                          description: Nombre del doctor
                        date:
                          type: string
                          description: Fecha de realización de la imagen
                        image:
                          type: string
                          description: Imagen en base64
                        title:
                          type: string
                          description: Titulo/nombre del estudio
                      x-apidog-orders:
                        - imageId
                        - title
                        - creatorName
                        - date
                        - image
                      required:
                        - imageId
                        - title
                        - creatorName
                        - date
                        - image
                      description: Imagen
                    description: Listado de imágenes
                    nullable: true
                x-apidog-orders:
                  - reportId
                  - images
                required:
                  - reportId
                  - images
              example:
                reportId: 7cc5a7f0-9510-4a71-a927-aaf14f1337de
                images:
                  - imageId: 838e5688-0c0f-460e-8cb6-86621730da5e
                    title: RMN Columna Lumbar
                    creatorName: Dr. Nicolas Garcia
                    date: '2025-02-22'
                    image: https://loremflickr.com/400/400?lock=3355484607829747
                  - imageId: ad6746cb-56f7-4ff1-9eb2-3fa4ad3b2359
                    title: Radiografía Lumbar
                    creatorName: Dr. Nicolas Garcia
                    date: '2025-04-10'
                    image: https://loremflickr.com/400/400?lock=5699819858316477
          headers: {}
          x-apidog-name: OK
        '400':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Código de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: Los parámetros ingresados son icorrectos o tienen faltantes.
                errorCode: '7'
          headers: {}
          x-apidog-name: Bad request
        '500':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Codigo de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: No se pudo recuperar la informacion del paciente
                errorCode: '7'
          headers: {}
          x-apidog-name: Internal server error
      security: []
      x-apidog-folder: Webhooks
      x-apidog-status: developing
      x-run-in-apidog: https://app.apidog.com/web/project/1259681/apis/api-33600325-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: https://uade-da2-backend.onrender.com
    description: Entorno producción
security: []

```
# v1/webhook/reportById

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/webhook/reportById:
    get:
      summary: v1/webhook/reportById
      deprecated: false
      description: Devuelve el detalle de un reporte especifico
      tags:
        - Webhooks
      parameters:
        - name: reportId
          in: query
          description: UUID del informe
          required: false
          example: >-
            338d03cb-e245-45b4-b2e0-e2a947e1d6c4338d03cb-e245-45b4-b2e0-e2a947e1d6c4
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  reportId:
                    type: string
                    description: UUID del informe
                    x-apidog-mock: '{{$string.uuid}}'
                  title:
                    type: string
                    description: Titulo/nombre del estudio
                  patientName:
                    type: string
                    description: Nombre del paciente
                  date:
                    type: string
                    description: Fecha de realizacion
                  status:
                    type: string
                    description: Estado del reporte
                  techniqueDetail:
                    type: string
                    description: Detalles técnicos del estudio
                  observations:
                    type: string
                    description: Observaciones del médico
                  conclusion:
                    type: string
                    description: Conclusiones del medico en base a sus observaciones
                x-apidog-orders:
                  - reportId
                  - title
                  - patientName
                  - date
                  - status
                  - techniqueDetail
                  - observations
                  - conclusion
                required:
                  - reportId
                  - title
                  - patientName
                  - date
                  - status
                  - techniqueDetail
                  - observations
                  - conclusion
              example:
                reportId: 338d03cb-e245-45b4-b2e0-e2a947e1d6c4
                title: Ecografía Renal Bilateral
                patientName: Juan Roman Upamecano
                date: '2025-09-05'
                status: INTERNACION
                techniqueDetails: >-
                  Radiografía de tórax en proyección posteroanterior (PA) y
                  lateral izquierda, realizada en inspiración completa con
                  adecuada técnica de exposición.
                observations: >-
                  Campos pulmonares de adecuada expansión. No se observan
                  infiltrados, consolidaciones ni imágenes de derrame pleural.
                  Silueta cardíaca dentro de límites normales con índice
                  cardiotorácico conservado. Trama broncovascular de
                  distribución habitual. Senos costofrénicos libres. Mediastino
                  centrado, sin ensanchamiento. Estructuras óseas sin lesiones
                  agudas evidentes..
                conclusion: >-
                  Estudio de tórax sin hallazgos patológicos significativos al
                  momento del examen. No se evidencian imágenes compatibles con
                  consolidación neumónica ni derrame pleural. Se sugiere
                  correlación clínica.
          headers: {}
          x-apidog-name: OK
        '400':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Código de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: Los parámetros ingresados son icorrectos o tienen faltantes.
                errorCode: '7'
          headers: {}
          x-apidog-name: Bad request
        '404':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                x-apidog-orders:
                  - message
                required:
                  - message
              example:
                message: La ruta solicitada no existe
                errorCode: '7'
          headers: {}
          x-apidog-name: Not Found
        '500':
          description: ''
          content:
            application/json:
              schema:
                title: ''
                type: object
                properties:
                  message:
                    type: string
                    description: Mensaje de error
                  errorCode:
                    type: string
                    description: Codigo de error
                x-apidog-orders:
                  - message
                  - errorCode
                required:
                  - message
                  - errorCode
              example:
                message: No se pudo recuperar la informacion del paciente
                errorCode: '7'
          headers: {}
          x-apidog-name: Internal server error
      security: []
      x-apidog-folder: Webhooks
      x-apidog-status: developing
      x-run-in-apidog: https://app.apidog.com/web/project/1259681/apis/api-33600164-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: https://uade-da2-backend.onrender.com
    description: Entorno producción
security: []

```
