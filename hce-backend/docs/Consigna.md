DESARROLLO DE APLICACIONES II
Ing. Joaquín Timerman
1
TRABAJO PRÁCTICO OBLIGATORIO
HEALTH GRID
La red de hospitales “Health Grid” busca unificar sus procesos médicos y administrativos. Actualmente, la información de los pacientes está dispersa en silos, lo que dificulta la atención coordinada.
Se solicita desarrollar una plataforma modular y distribuida que integre desde la Historia Clínica Electrónica hasta el monitoreo de pacientes en tiempo real.
REQUERIMIENTOS GENERALES
•
Cada grupo estará integrado por siete alumnos como máximo.
•
Cada grupo diseñará y desarrollará un módulo específico.
•
Cada módulo deberá integrarse con otros de acuerdo con las reglas de negocio establecidas en este documento. La integración será por medio de APIs RESTful y/o eventos asincrónicos, quedando la elección del método a criterio de cada grupo. Los mismos deberán estar justificados y correctamente defendidos en las entregas parciales y final.
•
Las tecnologías utilizadas para desarrollar cada módulo quedarán a criterio de cada grupo. Las mismas deberán estar justificadas y correctamente defendidas en las entregas parciales y final.
•
Se deberá documentar correctamente las APIs con herramientas como Swagger o Postman.
DESARROLLO DE APLICACIONES II
Ing. Joaquín Timerman
2
LISTADO DE MÓDULOS
1. Historia Clínica Electrónica
Es el repositorio central de datos médicos. Debe gestionar el registro de cada consulta, diagnóstico y tratamiento.
Registro Clínico: Creación y actualización de la ficha médica del paciente (antecedentes, alergias, cirugías, etc..).
Evolución Médica: Carga de notas de consulta por parte de profesionales de salud.
Consulta Externa: Exponer un servicio para que otros módulos consulten si un paciente tiene contraindicaciones médicas antes de un estudio o medicación.
Notificación Crítica: Emitir un evento asincrónico cuando se detecte una patología de notificación obligatoria.
2. Gestión de Turnos y Agendas
Administra la disponibilidad de profesionales y espacios físicos.
Calendario Profesional: Gestión de la disponibilidad horaria por médico, especialidad y sede.
Reserva de Turnos: Flujo de reserva para pacientes, permitiendo filtrar por cercanía o primera disponibilidad.
Recordatorios: Envío de notificaciones automáticas 24 horas antes del turno (vía evento asincrónico).
Presentismo: Registro de llegada del paciente para disparar el flujo de atención en sala de espera.
DESARROLLO DE APLICACIONES II
Ing. Joaquín Timerman
3
3. Farmacia e Insumos Hospitalarios
Controla el stock de medicamentos en farmacia y depósitos.
Dispensación de Recetas: Validación y entrega de medicamentos basados en la receta electrónica emitida en HCE.
Gestión de Inventario: Control de stock físico en farmacia central y depósitos de piso.
Alertas de Stock: Generación automática de pedidos de compra cuando un insumo crítico llega al punto de reorden.
Trazabilidad: Registro de qué lote de medicamento se entregó a cada paciente.
4. Laboratorio de Análisis Clínicos
Gestión de pedidos de laboratorio y carga de resultados.
Gestión de Ordenes: Recepción de pedidos de análisis desde el Portal del Paciente o Médicos.
Carga de Resultados: Interfaz para bioquímicos donde puedan cargar valores y observaciones técnicas.
Publicación de Resultados: Al guardar un resultado finalizado, debe impactar automáticamente en la HCE y notificar al paciente.
Validación de Rangos: Marcado automático de valores fuera de rango normal.
5. Diagnóstico por Imágenes
Gestión de estudios como Rayos X, Tomografías y Resonancias. Catálogo de Estudios: Gestión de turnos específicos para equipos de alta complejidad (Tomógrafos, Resonadores, etc.)
Informe Médico: Herramienta para que el radiólogo redacte el informe vinculado a la imagen.
Visualizador Lite: Interfaz para que el médico solicitante pueda ver el informe y el link a la imagen almacenada.
Integración de Resultados: Envío del informe finalizado a la HCE de forma sincrónica.
DESARROLLO DE APLICACIONES II
Ing. Joaquín Timerman
4
6. Internación y Gestión de Camas
Administra la ocupación de camas, ingresos a guardia y quirófanos.
Mapa de Camas: Visualización en tiempo real de la ocupación por piso, sector y tipo de cama (UTI, Sala Común, etc.)
Gestión de Ingresos: Registro de admisión desde Guardia o Cirugía programada.
Pases de Piso: Gestión de traslados internos del paciente y liberación de recursos.
Cierre de Episodio: Proceso de alta médica que dispara el evento para la limpieza de la unidad y la facturación final.
7. Facturación y Obras Sociales
Liquida las prestaciones médicas a las aseguradoras y gestiona cobros particulares.
Nomenclador Médico: Gestión de precios y convenios por cada obra social o prepaga.
Liquidación de prestaciones: Recopilación de todos los actos médicos (consultas, estudios, descartables) realizados a un paciente.
Auditoría de Cuentas: Proceso de validación de facturas antes del envío a la entidad pagadora.
Gestión de Coseguros: Cálculo y cobro de excedentes o copagos al paciente.
8. Portal del Paciente y Telemedicina
Interfaz para que el ciudadano interactúe con el sistema.
Mi Salud: Visualización de turnos próximos, historial de recetas y resultados de laboratorio.
Sala Virtual: Integración de videollamada para consultas de baja complejidad.
Pagos Online: Sección para pagar coseguros o turnos particulares utilizando saldo de tarjetas o billeteras virtuales (Pueden simular la integración).
Perfil y Notificaciones: Centro de notificaciones en tiempo real para alertas de salud y turnos.
DESARROLLO DE APLICACIONES II
Ing. Joaquín Timerman
5
9. Monitoreo de Pacientes
Simula el procesamiento de datos provenientes de dispositivos médicos.
Ingesta de Telemetría: Simulación de recepción de datos de sensores (frecuencia cardíaca, SpO2, etc.) mediante colas de mensajes.
Motor de Reglas: Evaluación en tiempo real de los datos recibidos (ej: si HR > 120 por 2 minutos, generar alerta).
Panel de Monitoreo: Dashboard para enfermería con el estado de los pacientes.
Alertas de Emergencia: Envío de evento de alta prioridad al Módulo de Internación ante un código rojo detectado por sensores.
10. Core
Gestión centralizada de usuarios (médicos, administrativos, pacientes), permisos y configuración global.
Maestro de Usuarios: Gestión de identidades para médicos, enfermeros, administrativos, bioquímicos y pacientes.
Control de Acceso: Definición de qué módulos y acciones puede realizar cada rol. Autenticación por JWT para todos los módulos.
Maestro de Sedes y Especialidades: Configuración global que consumen los módulos de Turnos e Integración.
Bus de Eventos: Configuración y auditoría de los canales de integración entre todos los módulos del sistema.
ENTREGAS
−
Primera entrega:
•
Mocks de cada vista (Frontend)
•
Contratos de APIs (Backend)
−
Segunda entrega:
•
Módulo completamente funcional con las integraciones mockeadas.
−
Entrega final:
•
Módulo completamente funcional e integrado al resto del sistema.
•
README con instrucciones para instalar y ejecutar el módulo.
DESARROLLO DE APLICACIONES II
Ing. Joaquín Timerman
6
Anexo - Glosario de Términos de Dominio
Conceptos Asistenciales (Atención al paciente)
-
HCE (Historia Clínica Electrónica): Registro longitudinal de la información de salud de un individuo, generada en uno o más encuentros en cualquier entorno de prestación de cuidados.
-
Episodio / Encuentro Médico: Una interacción específica entre un paciente y un profesional de la salud (una consulta, una internación, una guardia). Cada episodio debe generar un registro en la HCE.
-
Triage: Proceso de selección y clasificación de pacientes en los servicios de urgencias basado en sus necesidades terapéuticas y recursos disponibles, no necesariamente por orden de llegada.
-
Evolución: Nota clínica redactada por el profesional de salud durante un encuentro donde se describe el estado actual, el plan de tratamiento y las observaciones del paciente.
-
Receta Electrónica: Orden digital emitida por un médico para la dispensación de medicamentos.
Conceptos Administrativos y Financieros
-
Nomenclador Médico: Catálogo de todas las prestaciones médicas (consultas, cirugías, estudios) identificadas por un código único y una descripción. Es la base para la facturación.
-
Prestación Médica: Cualquier acción, servicio o estudio realizado a un paciente que tiene un costo asociado y debe ser registrado para su cobro.
-
Coseguro / Copago: Monto de dinero que el paciente debe abonar por una prestación médica, el cual no está cubierto por su obra social o prepaga.
-
Auditoría Médica: Proceso de revisión de las prestaciones realizadas para asegurar que cumplen con las normas médicas y administrativas antes de ser facturadas a la obra social.