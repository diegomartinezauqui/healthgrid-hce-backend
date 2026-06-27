"""
Router de desarrollo — solo se registra cuando APP_ENV != "production".
Provee un endpoint de login que emula al Módulo 10 (Core) y un Panel de Simulación.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.auth.dev_auth import DevLoginRequest, DevLoginResponse, generate_dev_token
from app.dependencies import DbSession
from app.models.paciente import Paciente

router = APIRouter()


@router.post(
    "/dev/paciente",
    summary="[DEV] Crear o confirmar paciente de prueba en la caché local",
    description="Inserta un paciente en la tabla local de HCE si no existe. Necesario antes de crear episodios en desarrollo.",
)
async def dev_crear_paciente(db: DbSession, id_paciente: int = 10500):
    result = await db.execute(select(Paciente).where(Paciente.id_paciente == id_paciente))
    paciente = result.scalar_one_or_none()
    if paciente:
        return {"status": "already_exists", "id_paciente": id_paciente}
    paciente = Paciente(
        id_paciente=id_paciente,
        datos_personales={
            "nombre": "Paciente Dev",
            "apellido": "Test",
            "dni": "00000000",
            "fecha_nacimiento": "1990-01-01",
            "sexo": "M",
        },
    )
    db.add(paciente)
    await db.commit()
    return {"status": "created", "id_paciente": id_paciente}


@router.post(
    "/dev/login",
    response_model=DevLoginResponse,
    summary="[DEV] Obtener token JWT de desarrollo",
    description=(
        "Genera un JWT firmado con la misma clave que Core (M10). "
        "El token funciona en todos los endpoints protegidos.\n\n"
        "**Sin body**: genera token con el usuario por defecto (dr.dev, rol médico, todos los permisos).\n\n"
        "**Con body**: permite personalizar sub, username, role, permissions y duración."
    ),
)
async def dev_login(body: Optional[DevLoginRequest] = None):
    return generate_dev_token(body)


@router.get(
    "/dev/simulador",
    response_class=HTMLResponse,
    summary="[DEV] Panel de Simulación de Integraciones",
    description="Interfaz interactiva para testear y simular las llamadas de los Módulos 2, 3, 4 y 5.",
)
async def dev_simulador():
    html_content = """<!DOCTYPE html>
<html lang="es" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HealthGrid HCE - Simulador de Integración</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Outfit', 'sans-serif'],
                        mono: ['Fira Code', 'monospace'],
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #0b0f19;
            background-image: radial-gradient(circle at 10% 20%, rgba(30, 41, 59, 0.5) 0%, transparent 80%),
                              radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.08) 0%, transparent 80%);
            background-attachment: fixed;
        }
        .glass-card {
            background: rgba(15, 23, 42, 0.65);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .console-log {
            background-color: #030712;
            border: 1px solid rgba(99, 102, 241, 0.2);
        }
    </style>
</head>
<body class="text-slate-200 min-h-screen pb-12 font-sans antialiased">
    <div class="max-w-6xl mx-auto px-4 pt-8">
        
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 pb-6 border-b border-slate-800">
            <div>
                <div class="flex items-center gap-3">
                    <span class="px-2.5 py-1 text-xs font-semibold bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">Módulos de Integración</span>
                    <span class="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse"></span>
                    <span class="text-xs text-emerald-400 font-medium">Servicios HCE Operativos</span>
                </div>
                <h1 class="text-3xl font-bold tracking-tight text-white mt-1 bg-gradient-to-r from-white via-slate-100 to-indigo-400 bg-clip-text text-transparent">
                    Simulador de Integración HealthGrid
                </h1>
                <p class="text-slate-400 text-sm mt-1">Pruebas locales de presentismo, dispensación de farmacia y webhooks de estudios.</p>
            </div>
            
            <!-- Auth Badge -->
            <div class="mt-4 md:mt-0 flex flex-col items-end">
                <div class="glass-card px-4 py-2.5 rounded-xl flex items-center gap-3 text-xs">
                    <div class="w-2 h-2 rounded-full bg-indigo-400"></div>
                    <div>
                        <span class="text-slate-400">JWT Autenticado:</span>
                        <span class="text-indigo-300 font-semibold font-mono" id="token-status">Obteniendo...</span>
                    </div>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex gap-2 p-1.5 bg-slate-900/60 rounded-xl mb-8 max-w-2xl border border-slate-800/80">
            <button onclick="switchTab('m2')" id="btn-m2" class="flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 text-white bg-indigo-600 shadow-md">
                M2 - Sala Espera
            </button>
            <button onclick="switchTab('m3')" id="btn-m3" class="flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 text-slate-400 hover:text-white">
                M3 - Farmacia
            </button>
            <button onclick="switchTab('m45')" id="btn-m45" class="flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 text-slate-400 hover:text-white">
                M4/M5 - Estudios
            </button>
            <button onclick="switchTab('m6')" id="btn-m6" class="flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 text-slate-400 hover:text-white">
                M6 - Camas
            </button>
        </nav>

        <!-- MAIN SECTIONS -->
        <main class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            
            <!-- Forms area (col-span-2) -->
            <div class="lg:col-span-2 space-y-6">
                
                <!-- TAB M2: Sala de Espera (Turnos) -->
                <section id="tab-m2" class="glass-card p-6 rounded-2xl shadow-xl space-y-6">
                    <div>
                        <h2 class="text-xl font-semibold text-white">Simulación Módulo 2: Presentismo de Turnos</h2>
                        <p class="text-slate-400 text-xs mt-1">Simula que un paciente llega a la clínica física y es admitido en la sala de espera para ser atendido.</p>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">ID del Paciente</label>
                            <input id="m2-paciente" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500" value="10500">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Sede Médica</label>
                            <input id="m2-sede" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500" value="1">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">ID del Médico</label>
                            <input id="m2-medico" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500" value="1">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">ID Turno (Opcional)</label>
                            <input id="m2-id-turno" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500" placeholder="Ej: 88402">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Fecha del Turno (Opcional)</label>
                            <input id="m2-fecha-turno" type="datetime-local" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Tipo de Atención</label>
                            <select id="m2-tipo" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                                <option value="guardia" selected>Guardia Médica</option>
                                <option value="consultorio">Consultorio Externo</option>
                                <option value="demanda_espontanea">Demanda Espontánea</option>
                                <option value="cirugia">Cirugía Programada</option>
                            </select>
                        </div>
                    </div>

                    <button onclick="admitirSalaEspera()" class="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium rounded-lg text-sm transition-all shadow-lg shadow-indigo-600/10 active:scale-[0.99]">
                        Registrar Presentismo en Sala de Espera
                    </button>
                </section>

                <!-- TAB M3: Farmacia (Recetas) -->
                <section id="tab-m3" class="glass-card p-6 rounded-2xl shadow-xl space-y-6 hidden">
                    <div class="flex justify-between items-start">
                        <div>
                            <h2 class="text-xl font-semibold text-white">Simulación Módulo 3: Dispensación de Farmacia</h2>
                            <p class="text-slate-400 text-xs mt-1">Busca las recetas médicas de un paciente por su ID y simula el proceso de dispensación de medicamentos.</p>
                        </div>
                    </div>

                    <div class="flex gap-2">
                        <input id="m3-paciente" type="number" class="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500" placeholder="ID Paciente (ej: 10500)" value="10500">
                        <button onclick="buscarRecetas()" class="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg text-sm transition-all border border-slate-700">
                            Buscar
                        </button>
                    </div>

                    <!-- List of Recipes -->
                    <div id="m3-recipes-container" class="space-y-4">
                        <p class="text-slate-500 text-center text-sm py-8">Realiza una búsqueda para listar las recetas.</p>
                    </div>
                </section>

                <!-- TAB M4/M5: Estudios y Resultados -->
                <section id="tab-m45" class="glass-card p-6 rounded-2xl shadow-xl space-y-6 hidden">
                    <div>
                        <h2 class="text-xl font-semibold text-white">Simulación Módulos 4 y 5: Resultados de Estudios</h2>
                        <p class="text-slate-400 text-xs mt-1">Envía los resultados de análisis bioquímicos (M4) o de radiología/imágenes (M5) vinculados a una orden médica en HCE.</p>
                    </div>

                    <div class="flex justify-end gap-2 mb-2">
                        <button onclick="cargarOrdenesPendientes()" class="px-3.5 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-750 text-slate-300 rounded-lg transition-all">
                            🔄 Actualizar Órdenes Pendientes
                        </button>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        
                        <!-- M4 Laboratorio -->
                        <div class="space-y-4 p-4 bg-slate-900/40 rounded-xl border border-slate-850">
                            <h3 class="font-semibold text-indigo-400 text-sm flex items-center gap-2">
                                <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span> Módulo 4: Webhook Laboratorio
                            </h3>
                            <div class="space-y-3" id="m4-orders-container">
                                <p class="text-slate-500 text-xs py-4 text-center">Cargando órdenes...</p>
                            </div>
                        </div>

                        <!-- M5 Imagenes -->
                        <div class="space-y-4 p-4 bg-slate-900/40 rounded-xl border border-slate-850">
                            <h3 class="font-semibold text-indigo-400 text-sm flex items-center gap-2">
                                <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span> Módulo 5: Informes de Imágenes
                            </h3>
                            <div class="space-y-3" id="m5-orders-container">
                                <p class="text-slate-500 text-xs py-4 text-center">Cargando órdenes...</p>
                            </div>
                        </div>

                    </div>
                </section>

                <!-- TAB M6: Camas / Internación -->
                <section id="tab-m6" class="glass-card p-6 rounded-2xl shadow-xl space-y-6 hidden">
                    <div>
                        <h2 class="text-xl font-semibold text-white">Simulación Módulo 6: Gestión de Camas e Internación</h2>
                        <p class="text-slate-400 text-xs mt-1">Ciclo completo: Crear episodio → Solicitar cama → Simular respuesta M6 → Registrar ingreso.</p>
                    </div>

                    <!-- Paso 1: Configurar paciente y episodio -->
                    <div class="p-4 bg-slate-900/50 rounded-xl border border-slate-800 space-y-3">
                        <h3 class="text-sm font-semibold text-indigo-400 uppercase tracking-wider">Paso 1 — Preparar Paciente y Episodio</h3>
                        <div class="flex gap-3 items-end">
                            <div class="flex-1">
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">ID Paciente</label>
                                <input id="m6-id-paciente" type="number" value="10500" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <div class="flex-1">
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Tipo de Episodio</label>
                                <select id="m6-tipo-episodio" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                                    <option value="guardia">Guardia</option>
                                    <option value="internacion">Internación</option>
                                    <option value="consulta_externa">Consulta Externa</option>
                                </select>
                            </div>
                            <button onclick="seedPacienteYCrearEpisodio()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg text-sm transition-all">
                                Crear Episodio
                            </button>
                        </div>
                        <div class="flex gap-3 items-end pt-2 border-t border-slate-800/50">
                            <div class="flex-1">
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">O Cargar ID de Episodio Existente</label>
                                <input id="m6-id-episodio-existente" type="number" placeholder="Ej: 12" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <button onclick="cargarEpisodioExistenteM6()" class="px-4 py-2 bg-slate-850 hover:bg-slate-750 border border-slate-700 text-white font-medium rounded-lg text-sm transition-all">
                                Cargar Episodio
                            </button>
                        </div>
                        <div id="m6-episodio-status" class="text-xs text-slate-500 font-mono mt-2">
                            Sin episodio activo. Crea uno o carga uno existente arriba.
                        </div>
                    </div>

                    <!-- Paso 2 y 3: dos columnas -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">

                        <!-- Paso 2: Crear Solicitud de Cama -->
                        <div class="p-4 bg-slate-900/40 rounded-xl border border-slate-800 space-y-3">
                            <h3 class="text-sm font-semibold text-indigo-400 uppercase tracking-wider">Paso 2 — Solicitar Cama (HCE → M6)</h3>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Tipo</label>
                                <select id="m6-tipo-sol" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                                    <option value="internacion">Internación</option>
                                    <option value="pase">Pase de cama</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Prioridad</label>
                                <select id="m6-prioridad-sol" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                                    <option value="Alta">Alta</option>
                                    <option value="Media" selected>Media</option>
                                    <option value="Baja">Baja</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Sector</label>
                                <input id="m6-sector-sol" type="text" value="UTI — Unidad de Terapia Intensiva" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Motivo clínico</label>
                                <input id="m6-motivo-sol" type="text" value="Paciente requiere monitoreo intensivo." class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <button onclick="crearSolicitudCamaM6()" class="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium rounded-lg text-sm transition-all">
                                Crear Solicitud de Cama
                            </button>
                        </div>

                        <!-- Paso 3: Ver solicitudes activas -->
                        <div class="p-4 bg-slate-900/40 rounded-xl border border-slate-800 space-y-3">
                            <div class="flex justify-between items-center">
                                <h3 class="text-sm font-semibold text-indigo-400 uppercase tracking-wider">Paso 3 — Solicitudes del Episodio</h3>
                                <button onclick="cargarSolicitudesM6()" class="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg transition-all">
                                    Actualizar
                                </button>
                            </div>
                            <div id="m6-solicitudes-container" class="space-y-2">
                                <p class="text-slate-500 text-xs text-center py-6">Crea un episodio y una solicitud para verla aquí.</p>
                            </div>
                        </div>

                    </div>

                    <!-- Paso 4: Simular Ingreso (M6 → HCE) -->
                    <div class="p-4 bg-slate-900/40 rounded-xl border border-indigo-500/20 space-y-3">
                        <h3 class="text-sm font-semibold text-indigo-400 uppercase tracking-wider">Paso 4 — Simular Callback M6 → HCE <span class="text-slate-500 text-[10px] font-normal">POST /internacion/ingreso</span></h3>
                        <p class="text-slate-400 text-xs">Simula que M6 ya asignó una cama y notifica el ingreso físico del paciente. Esto crea el Episodio de Internación en la HCE.</p>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">ID Episodio (opcional)</label>
                                <input id="m6-cb-id-episodio" type="number" placeholder="Auto" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Sector</label>
                                <input id="m6-cb-sector" type="text" value="UTI" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Habitación</label>
                                <input id="m6-cb-habitacion" type="text" value="Terapia A" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Cama</label>
                                <input id="m6-cb-cama" type="text" value="Cama 4" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500">
                            </div>
                        </div>
                        <button onclick="simularIngresoM6()" class="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-medium rounded-lg text-sm transition-all">
                            Simular Ingreso de M6 (POST /internacion/ingreso)
                        </button>
                    </div>
                </section>

            </div>

            <!-- Terminal logs (col-span-1) -->
            <div class="space-y-4">
                <div class="glass-card p-4 rounded-2xl flex flex-col h-[520px]">
                    <div class="flex justify-between items-center pb-3 border-b border-slate-800 mb-3">
                        <div class="flex items-center gap-2">
                            <span class="w-3 h-3 bg-indigo-500/20 text-indigo-400 rounded flex items-center justify-center font-mono text-[9px]">>_</span>
                            <span class="text-xs font-semibold text-slate-300 tracking-wide uppercase">Consola de HTTP requests</span>
                        </div>
                        <button onclick="clearConsole()" class="text-[10px] text-slate-500 hover:text-slate-300 transition-colors uppercase">Limpiar</button>
                    </div>
                    <div id="console" class="flex-1 font-mono text-[11px] overflow-y-auto space-y-2 p-3 console-log rounded-xl scrollbar-thin scrollbar-thumb-slate-800">
                        <div class="text-indigo-400/70">[SISTEMA] Listo para pruebas. El token de desarrollo se generará automáticamente.</div>
                    </div>
                </div>
            </div>

        </main>
    </div>

    <!-- Scripting for simulator -->
    <script>
        let devToken = "";
        const apiPrefix = "/api/v1";

        // Switch Tabs
        function switchTab(tabId) {
            const tabs = ['m2', 'm3', 'm45', 'm6'];
            tabs.forEach(t => {
                document.getElementById(`tab-${t}`).classList.add('hidden');
                document.getElementById(`btn-${t}`).className = "flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 text-slate-400 hover:text-white";
            });
            document.getElementById(`tab-${tabId}`).classList.remove('hidden');
            document.getElementById(`btn-${tabId}`).className = "flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 text-white bg-indigo-600 shadow-md";

            if (tabId === 'm45') {
                cargarOrdenesPendientes();
            }
        }

        // Output to mock console
        function logToConsole(message, type = 'info') {
            const consoleDiv = document.getElementById('console');
            const time = new Date().toLocaleTimeString();
            let color = 'text-slate-400';
            if (type === 'success') color = 'text-emerald-400';
            if (type === 'error') color = 'text-rose-400';
            if (type === 'sent') color = 'text-sky-400';

            const logItem = document.createElement('div');
            logItem.className = `${color} border-b border-slate-900/60 pb-1`;
            logItem.innerHTML = `<span class="text-slate-600">[${time}]</span> ${message}`;
            consoleDiv.appendChild(logItem);
            consoleDiv.scrollTop = consoleDiv.scrollHeight;
        }

        function clearConsole() {
            document.getElementById('console').innerHTML = '';
        }

        // Auto authenticate on dev login
        async function authenticate() {
            try {
                const res = await fetch(`${apiPrefix}/dev/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                if (res.ok) {
                    const data = await res.json();
                    devToken = data.access_token;
                    document.getElementById('token-status').innerText = 'ACTIVO (ID:1)';
                    document.getElementById('token-status').className = 'text-emerald-400 font-semibold font-mono';
                    logToConsole('🔑 Autenticación exitosa (Token de Desarrollo inyectado)', 'success');
                } else {
                    logToConsole('❌ Error de generación de token de desarrollo', 'error');
                }
            } catch (e) {
                logToConsole(`❌ Error de red al autenticar: ${e.message}`, 'error');
            }
        }

        // M2 Admit Patient
        async function admitirSalaEspera() {
            const pacienteId = document.getElementById('m2-paciente').value;
            const sedeId = document.getElementById('m2-sede').value;
            const medicoId = document.getElementById('m2-medico').value;
            const idTurno = document.getElementById('m2-id-turno').value;
            const fechaTurno = document.getElementById('m2-fecha-turno').value;
            const tipo = document.getElementById('m2-tipo').value;

            if (!pacienteId || !sedeId || !medicoId) {
                alert('Faltan campos obligatorios');
                return;
            }

            const url = `${apiPrefix}/sala-espera/ingreso`;
            const payload = {
                id_paciente: parseInt(pacienteId),
                id_sede: parseInt(sedeId),
                id_medico: parseInt(medicoId),
                tipo_atencion: tipo
            };

            if (idTurno) {
                payload.id_turno_m2 = parseInt(idTurno);
            }
            if (fechaTurno) {
                payload.fecha_turno = new Date(fechaTurno).toISOString();
            }

            logToConsole(`POST ${url} <br> Payload: ${JSON.stringify(payload)}`, 'sent');

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${devToken}`
                    },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`✅ 201 Created: Paciente en sala de espera. Registro ID: ${data.id_espera}`, 'success');
                } else {
                    logToConsole(`❌ ${res.status} Bad Request: ${JSON.stringify(data.detail)}`, 'error');
                }
            } catch (e) {
                logToConsole(`❌ Error de red: ${e.message}`, 'error');
            }
        }

        // M3 Buscar Recetas
        async function buscarRecetas() {
            const pacienteId = document.getElementById('m3-paciente').value;
            if (!pacienteId) {
                alert('Ingrese el ID del paciente');
                return;
            }

            const url = `${apiPrefix}/recetas?id_paciente=${pacienteId}`;
            logToConsole(`GET ${url}`, 'sent');

            try {
                const res = await fetch(url, {
                    headers: { 'Authorization': `Bearer ${devToken}` }
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`✅ 200 OK: Obtenidas ${data.total} recetas`, 'success');
                    renderRecipes(data.data);
                } else {
                    logToConsole(`❌ ${res.status} Error al traer recetas`, 'error');
                }
            } catch (e) {
                logToConsole(`❌ Error de red: ${e.message}`, 'error');
            }
        }

        function renderRecipes(recipes) {
            const container = document.getElementById('m3-recipes-container');
            if (recipes.length === 0) {
                container.innerHTML = '<p class="text-slate-500 text-center text-sm py-4">No se encontraron recetas para este paciente.</p>';
                return;
            }

            container.innerHTML = recipes.map(r => {
                const badgeColor = r.estado === 'Activa' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                const itemsHtml = r.items.map(i => `
                    <div class="text-xs text-slate-300 font-mono mt-1 pl-2 border-l border-slate-700">
                        • <strong>${i.medicamento}</strong> - Cantidad: ${i.cantidad} <span class="text-slate-400 font-sans italic">(${i.indicaciones})</span>
                    </div>
                `).join('');

                const btnHtml = r.estado === 'Activa' 
                    ? `<button onclick="dispensarReceta(${r.id_receta})" class="mt-3 px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded transition-all active:scale-[0.98]">
                         Marcar como Dispensada (Farmacia M3)
                       </button>`
                    : '';

                return `
                    <div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-white">Receta #${r.id_receta}</span>
                            <span class="px-2 py-0.5 text-[10px] font-semibold border rounded-full ${badgeColor}">${r.estado}</span>
                        </div>
                        <div class="py-1">
                            ${itemsHtml}
                        </div>
                        ${btnHtml}
                    </div>
                `;
            }).join('');
        }

        // M3 Dispensar Receta
        async function dispensarReceta(idReceta) {
            const url = `${apiPrefix}/recetas/${idReceta}/dispensar`;
            logToConsole(`PATCH ${url}`, 'sent');

            try {
                const res = await fetch(url, {
                    method: 'PATCH',
                    headers: { 'Authorization': `Bearer ${devToken}` }
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`✅ 200 OK: Receta #${idReceta} Dispensada exitosamente!`, 'success');
                    buscarRecetas(); // Refresh recipes list
                } else {
                    logToConsole(`❌ ${res.status} Error: ${data.detail.message}`, 'error');
                }
            } catch (e) {
                logToConsole(`❌ Error de red: ${e.message}`, 'error');
            }
        }

        // Load study orders
        async function cargarOrdenesPendientes() {
            const containerM4 = document.getElementById('m4-orders-container');
            const containerM5 = document.getElementById('m5-orders-container');
            containerM4.innerHTML = '<p class="text-slate-500 text-xs py-4 text-center">Cargando...</p>';
            containerM5.innerHTML = '<p class="text-slate-500 text-xs py-4 text-center">Cargando...</p>';

            try {
                // Fetch Laboratorio
                const resM4 = await fetch(`${apiPrefix}/ordenes?tipo_estudio=Laboratorio&estado=Pendiente`, {
                    headers: { 'Authorization': `Bearer ${devToken}` }
                });
                const dataM4 = await resM4.json();

                // Fetch Imagenes
                const resM5 = await fetch(`${apiPrefix}/ordenes?tipo_estudio=Imagen&estado=Pendiente`, {
                    headers: { 'Authorization': `Bearer ${devToken}` }
                });
                const dataM5 = await resM5.json();

                renderOrdersM4(dataM4.data || []);
                renderOrdersM5(dataM5.data || []);
            } catch (e) {
                logToConsole(`❌ Error cargando órdenes para simulación: ${e.message}`, 'error');
            }
        }

        // Mappings and catalogs for simulation richness
        const M4_ESTUDIOS_CATALOGO = {
            1: "Hemograma completo",
            2: "Perfil lipídico (Colesterol, Triglicéridos)",
            3: "Glucemia en ayunas",
            4: "Función Renal (Urea, Creatinina)",
            5: "Hepatograma completo",
            101: "Hemograma",
            102: "Hepatograma"
        };

        const M5_MODALIDADES = {
            "ECOGRAFY": "Ecografía",
            "RADIOLOGY": "Radiografía",
            "TOMOGRAPHY": "Tomografía",
            "RESONANCE": "Resonancia",
            "MAMMOGRAPHY": "Mamografía",
            "DENSITOMETRY": "Densitometría",
            "ECODOPPLER": "Ecodoppler",
            "ENDOSCOPY": "Endoscopia"
        };

        const M4_ESTUDIOS_DETALLES = {
            1: [
                { nombre: "Hemoglobina", valor: 14.2, unidad: "g/dL", rango_normal: { min: 12.0, max: 16.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "Hematocrito", valor: 42.5, unidad: "%", rango_normal: { min: 37.0, max: 48.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "Glóbulos Blancos", valor: 7500, unidad: "/mm3", rango_normal: { min: 4500, max: 11000 }, fuera_de_rango: false, es_critico: false }
            ],
            2: [
                { nombre: "Colesterol Total", valor: 240.0, unidad: "mg/dL", rango_normal: { min: 120.0, max: 200.0 }, fuera_de_rango: true, es_critico: false, observacion: "Elevado" },
                { nombre: "Triglicéridos", valor: 155.0, unidad: "mg/dL", rango_normal: { min: 40.0, max: 150.0 }, fuera_de_rango: true, es_critico: false },
                { nombre: "Colesterol HDL", valor: 45.0, unidad: "mg/dL", rango_normal: { min: 40.0, max: 60.0 }, fuera_de_rango: false, es_critico: false }
            ],
            3: [
                { nombre: "Glucosa", valor: 95.0, unidad: "mg/dL", rango_normal: { min: 70.0, max: 100.0 }, fuera_de_rango: false, es_critico: false }
            ],
            4: [
                { nombre: "Urea", valor: 35.0, unidad: "mg/dL", rango_normal: { min: 15.0, max: 45.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "Creatinina", valor: 0.9, unidad: "mg/dL", rango_normal: { min: 0.6, max: 1.2 }, fuera_de_rango: false, es_critico: false }
            ],
            5: [
                { nombre: "TGO (AST)", valor: 25.0, unidad: "U/L", rango_normal: { min: 5.0, max: 40.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "TGP (ALT)", valor: 28.0, unidad: "U/L", rango_normal: { min: 5.0, max: 40.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "Fosfatasa Alcalina", valor: 180.0, unidad: "U/L", rango_normal: { min: 40.0, max: 250.0 }, fuera_de_rango: false, es_critico: false }
            ],
            101: [
                { nombre: "Hemoglobina", valor: 13.8, unidad: "g/dL", rango_normal: { min: 12.0, max: 16.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "Glóbulos Blancos", valor: 6800, unidad: "/mm3", rango_normal: { min: 4500, max: 11000 }, fuera_de_rango: false, es_critico: false }
            ],
            102: [
                { nombre: "TGO (AST)", valor: 22.0, unidad: "U/L", rango_normal: { min: 5.0, max: 40.0 }, fuera_de_rango: false, es_critico: false },
                { nombre: "TGP (ALT)", valor: 24.0, unidad: "U/L", rango_normal: { min: 5.0, max: 40.0 }, fuera_de_rango: false, es_critico: false }
            ]
        };

        function renderOrdersM4(orders) {
            const container = document.getElementById('m4-orders-container');
            if (orders.length === 0) {
                container.innerHTML = '<p class="text-slate-500 text-xs py-4 text-center">No hay órdenes de laboratorio pendientes.</p>';
                return;
            }

            container.innerHTML = orders.map(o => {
                const estudiosNombres = o.estudio_ids && o.estudio_ids.length > 0
                    ? o.estudio_ids.map(id => M4_ESTUDIOS_CATALOGO[id] || `Estudio #${id}`).join(', ')
                    : 'Análisis general';

                return `
                    <div class="p-3 bg-slate-950/80 border border-slate-850 rounded-lg space-y-2 text-xs">
                        <div class="flex justify-between">
                            <span class="font-semibold text-slate-300">Orden #${o.id_orden}</span>
                            <span class="text-amber-500 font-medium font-mono">Prioridad: ${o.prioridad}</span>
                        </div>
                        <div class="text-slate-400">${o.descripcion_pedido || 'Estudio de Laboratorio'}</div>
                        <div class="text-[10px] text-indigo-400 font-medium bg-indigo-500/5 px-2 py-1 rounded border border-indigo-500/10">
                            <strong>Estudios solicitados:</strong> ${estudiosNombres}
                        </div>
                        <button onclick='simularWebhookM4(${o.id_orden}, ${o.id_paciente}, "${o.descripcion_pedido || 'Análisis bioquímico'}", ${JSON.stringify(o.estudio_ids || [])})' class="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium transition-all active:scale-[0.98] mt-2">
                            Simular Webhook Resultado M4
                        </button>
                    </div>
                `;
            }).join('');
        }

        function renderOrdersM5(orders) {
            const container = document.getElementById('m5-orders-container');
            if (orders.length === 0) {
                container.innerHTML = '<p class="text-slate-500 text-xs py-4 text-center">No hay órdenes de imágenes pendientes.</p>';
                return;
            }

            container.innerHTML = orders.map(o => {
                const modNombre = o.subtipo ? M5_MODALIDADES[o.subtipo] || o.subtipo : 'No especificada';

                return `
                    <div class="p-3 bg-slate-950/80 border border-slate-850 rounded-lg space-y-3 text-xs">
                        <div class="flex justify-between">
                            <span class="font-semibold text-slate-300">Orden #${o.id_orden}</span>
                            <span class="text-amber-500 font-medium font-mono">Prioridad: ${o.prioridad}</span>
                        </div>
                        <div class="text-slate-400 mb-1">${o.descripcion_pedido || 'Estudio de Imágenes'}</div>
                        <div class="text-[10px] text-indigo-400 font-medium bg-indigo-500/5 px-2 py-1 rounded border border-indigo-500/10">
                            <strong>Modalidad solicitada:</strong> ${modNombre} (${o.subtipo || 'S/D'})
                        </div>
                        
                        <div class="space-y-1.5 pt-1.5 border-t border-slate-850">
                            <label class="block text-[9px] uppercase tracking-wider text-slate-500 font-semibold">Confirmar Modalidad</label>
                            <select id="m5-subtipo-${o.id_orden}" class="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[10px] text-slate-200 focus:outline-none">
                                <option value="ECOGRAFY" ${o.subtipo === 'ECOGRAFY' ? 'selected' : ''}>ECOGRAFY (Ecografía)</option>
                                <option value="RADIOLOGY" ${o.subtipo === 'RADIOLOGY' ? 'selected' : ''}>RADIOLOGY (Radiografía)</option>
                                <option value="TOMOGRAPHY" ${o.subtipo === 'TOMOGRAPHY' ? 'selected' : ''}>TOMOGRAPHY (Tomografía)</option>
                                <option value="RESONANCE" ${o.subtipo === 'RESONANCE' ? 'selected' : ''}>RESONANCE (Resonancia)</option>
                                <option value="MAMMOGRAPHY" ${o.subtipo === 'MAMMOGRAPHY' ? 'selected' : ''}>MAMMOGRAPHY (Mamografía)</option>
                                <option value="DENSITOMETRY" ${o.subtipo === 'DENSITOMETRY' ? 'selected' : ''}>DENSITOMETRY (Densitometría)</option>
                                <option value="ECODOPPLER" ${o.subtipo === 'ECODOPPLER' ? 'selected' : ''}>ECODOPPLER (Ecodoppler)</option>
                                <option value="ENDOSCOPY" ${o.subtipo === 'ENDOSCOPY' ? 'selected' : ''}>ENDOSCOPY (Endoscopia)</option>
                            </select>
                            <label class="block text-[9px] uppercase tracking-wider text-slate-500 font-semibold mt-1">PACS Link</label>
                            <input id="m5-pacs-${o.id_orden}" type="text" class="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[10px] text-indigo-300 font-mono focus:outline-none" value="https://viewer.pacs.hospital/study/838e5688">
                            <label class="block text-[9px] uppercase tracking-wider text-slate-500 font-semibold mt-1">Texto del Informe</label>
                            <input id="m5-informe-${o.id_orden}" type="text" class="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[10px] text-slate-200 focus:outline-none" value="Resultados normales sin hallazgos patológicos.">
                        </div>

                        <button onclick="simularM5Result(${o.id_orden}, ${o.id_paciente}, '${o.descripcion_pedido || 'Ecografía'}')" class="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium transition-all active:scale-[0.98]">
                            Enviar Resultado Imagen M5
                        </button>
                    </div>
                `;
            }).join('');
        }

        // Simulate M4 Webhook
        async function simularWebhookM4(idOrden, idPaciente, descripcion, estudioIds) {
            const url = `${apiPrefix}/webhook/laboratorio/resultado`;
            
            // Build analitos based on study IDs
            let analitos = [];
            if (estudioIds && estudioIds.length > 0) {
                estudioIds.forEach(id => {
                    const mockAnalitos = M4_ESTUDIOS_DETALLES[id];
                    if (mockAnalitos) {
                        analitos = analitos.concat(JSON.parse(JSON.stringify(mockAnalitos)));
                    }
                });
            }
            
            // Fallback if no analitos were found
            if (analitos.length === 0) {
                analitos = [
                    {
                        nombre: "Glucosa",
                        valor: 95.0,
                        unidad: "mg/dL",
                        rango_normal: { min: 70.0, max: 100.0 },
                        fuera_de_rango: false,
                        es_critico: false,
                        observacion: "Valores en ayuno"
                    }
                ];
            }
            
            const total_analitos = analitos.length;
            const analitos_fuera_de_rango = analitos.filter(a => a.fuera_de_rango).length;
            const hay_valores_criticos = analitos.some(a => a.es_critico);

            const payload = {
                evento: "laboratorio.resultado_listo",
                version: "1.0",
                id_evento: "uuid-simulado-" + Math.floor(Math.random() * 10000),
                fecha_ocurrencia: new Date().toISOString(),
                orden: {
                    id_laboratorio: Math.floor(Math.random() * 100) + 1,
                    id_orden_hce: idOrden,
                    descripcion: descripcion,
                    prioridad: "Routine",
                    fecha_solicitud: new Date(Date.now() - 3600000).toISOString(),
                    fecha_resultado: new Date().toISOString()
                },
                paciente: {
                    id: idPaciente,
                    nombre: "Paciente Prueba",
                    dni: "12345678"
                },
                profesional_firmante: "Dra. García (Simulación M4)",
                resumen: {
                    total_analitos: total_analitos,
                    analitos_fuera_de_rango: analitos_fuera_de_rango,
                    hay_valores_criticos: hay_valores_criticos
                },
                analitos: analitos
            };

            logToConsole(`POST ${url} <br> Webhook Payload: ${JSON.stringify(payload)}`, 'sent');

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${devToken}`
                    },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`✅ 201 Created: Webhook de Laboratorio procesado. Orden #${idOrden} FINALIZADA.`, 'success');
                    cargarOrdenesPendientes();
                } else {
                    logToConsole(`❌ ${res.status} Error procesando webhook`, 'error');
                }
            } catch (e) {
                logToConsole(`❌ Error de red: ${e.message}`, 'error');
            }
        }

        // Simulate M5 Results
        async function simularM5Result(idOrden, idPaciente, descripcion) {
            const url = `${apiPrefix}/resultados`;
            const subtipo = document.getElementById(`m5-subtipo-${idOrden}`).value;
            const pacsLink = document.getElementById(`m5-pacs-${idOrden}`).value;
            const informe = document.getElementById(`m5-informe-${idOrden}`).value;

            const payload = {
                id_orden: idOrden,
                id_paciente: idPaciente,
                tipo_estudio: "Imagen",
                id_profesional_firmante: "Dr. Nicolas Garcia (Simulación M5)",
                fecha_resultado: new Date().toISOString(),
                informe_resumen: descripcion,
                id_externo_estudio: "report-uuid-" + Math.floor(Math.random() * 10000),
                subtipo: subtipo,
                link_imagen: pacsLink,
                url_detalle: "https://api.imagenes.hospital/v1/estudios/" + idOrden + "/completo"
            };

            logToConsole(`POST ${url} <br> Payload: ${JSON.stringify(payload)}`, 'sent');

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${devToken}`
                    },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`✅ 21 Created: Resultado de Imagen registrado. Orden #${idOrden} FINALIZADA.`, 'success');
                    cargarOrdenesPendientes();
                } else {
                    logToConsole(`❌ ${res.status} Error registrando resultado`, 'error');
                }
            } catch (e) {
                logToConsole(`❌ Error de red: ${e.message}`, 'error');
            }
        }

        // ─── M6: Camas ────────────────────────────────────────────────
        let m6EpisodioId = null;
        let m6PacienteId = 10500;

        async function seedPacienteYCrearEpisodio() {
            const idPaciente = parseInt(document.getElementById('m6-id-paciente').value) || 10500;
            // Primero asegurar que el paciente existe en la caché local
            try {
                const res = await fetch(`/api/v1/dev/paciente?id_paciente=${idPaciente}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${devToken}` }
                });
                const data = await res.json();
                if (res.ok) {
                    const msg = data.status === 'created'
                        ? `Paciente #${idPaciente} creado en la cache local.`
                        : `Paciente #${idPaciente} ya existia en la cache local.`;
                    logToConsole(msg, 'success');
                } else {
                    logToConsole(`Error al seed paciente: ${JSON.stringify(data)}`, 'error');
                    return;
                }
            } catch (e) {
                logToConsole(`Error: ${e.message}`, 'error');
                return;
            }
            await crearEpisodioM6();
        }

        async function cargarEpisodioExistenteM6() {
            const idPaciente = parseInt(document.getElementById('m6-id-paciente').value) || 10500;
            const idEpisodio = parseInt(document.getElementById('m6-id-episodio-existente').value);
            if (!idEpisodio) {
                alert('Ingresa un ID de episodio válido.');
                return;
            }
            m6PacienteId = idPaciente;
            m6EpisodioId = idEpisodio;
            document.getElementById('m6-cb-id-episodio').value = m6EpisodioId;
            document.getElementById('m6-episodio-status').innerHTML =
                `<span class="text-indigo-400 font-semibold">Episodio #${m6EpisodioId} cargado</span> — Paciente ${idPaciente}`;
            logToConsole(`Episodio #${m6EpisodioId} configurado manualmente. Listando solicitudes...`, 'success');
            await cargarSolicitudesM6();
        }

        async function crearEpisodioM6() {
            const idPaciente = parseInt(document.getElementById('m6-id-paciente').value) || 10500;
            m6PacienteId = idPaciente;
            const tipo = document.getElementById('m6-tipo-episodio').value;
            const url = `/api/v1/patients/${idPaciente}/episodes`;
            const payload = { tipo, id_sede: 1, diagnostico_principal: 'Episodio de prueba — simulacion M6' };
            logToConsole(`POST ${url} — Crear episodio tipo "${tipo}"`, 'sent');
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${devToken}` },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    m6EpisodioId = data.id_episodio;
                    document.getElementById('m6-cb-id-episodio').value = m6EpisodioId;
                    document.getElementById('m6-episodio-status').innerHTML =
                        `<span class="text-emerald-400 font-semibold">Episodio #${m6EpisodioId} activo</span> — Paciente ${idPaciente} | Tipo: ${tipo}`;
                    logToConsole(`201 OK — Episodio #${m6EpisodioId} creado. Listo para solicitar cama.`, 'success');
                    await cargarSolicitudesM6();
                } else {
                    logToConsole(`${res.status} Error: ${JSON.stringify(data.detail)}`, 'error');
                }
            } catch (e) { logToConsole(`Error: ${e.message}`, 'error'); }
        }

        async function crearSolicitudCamaM6() {
            if (!m6EpisodioId) { alert('Primero crea un episodio (Paso 1).'); return; }
            const url = `/api/v1/patients/${m6PacienteId}/episodes/${m6EpisodioId}/solicitudes-cama`;
            const payload = {
                tipo: document.getElementById('m6-tipo-sol').value,
                prioridad: document.getElementById('m6-prioridad-sol').value,
                sector: document.getElementById('m6-sector-sol').value || undefined,
                motivo: document.getElementById('m6-motivo-sol').value || undefined,
            };
            logToConsole(`POST ${url} — Payload: ${JSON.stringify(payload)}`, 'sent');
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${devToken}` },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`201 OK — Solicitud #${data.id_solicitud} creada. Estado: ${data.estado}. M6 notificado (mock).`, 'success');
                    await cargarSolicitudesM6();
                } else {
                    logToConsole(`${res.status} Error: ${JSON.stringify(data.detail)}`, 'error');
                }
            } catch (e) { logToConsole(`Error: ${e.message}`, 'error'); }
        }

        async function cargarSolicitudesM6() {
            if (!m6EpisodioId) return;
            const url = `/api/v1/patients/${m6PacienteId}/episodes/${m6EpisodioId}/solicitudes-cama`;
            try {
                const res = await fetch(url, { headers: { 'Authorization': `Bearer ${devToken}` } });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`GET ${url} — ${data.solicitudes.length} solicitudes encontradas.`, 'success');
                    renderSolicitudesM6(data);
                }
            } catch (e) { logToConsole(`Error cargando solicitudes: ${e.message}`, 'error'); }
        }

        function renderSolicitudesM6(data) {
            const container = document.getElementById('m6-solicitudes-container');
            const colores = {
                'Pendiente': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
                'Aceptada':  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
                'Rechazada': 'bg-rose-500/10 text-rose-400 border-rose-500/20',
                'Cancelada': 'bg-slate-500/10 text-slate-400 border-slate-500/20',
            };
            let camaHtml = '';
            if (data.internado && data.cama_actual) {
                const c = data.cama_actual;
                camaHtml = `<div class="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs mb-2">
                    <span class="text-emerald-400 font-semibold">INTERNADO</span>
                    <span class="text-slate-300 ml-2">${c.sector || ''} | ${c.habitacion || ''} | ${c.cama || ''}</span>
                </div>`;
            }
            if (!data.solicitudes || data.solicitudes.length === 0) {
                container.innerHTML = camaHtml + '<p class="text-slate-500 text-xs text-center py-4">Sin solicitudes para este episodio.</p>';
                return;
            }
            container.innerHTML = camaHtml + data.solicitudes.map(s => {
                const badge = colores[s.estado] || 'bg-slate-700 text-slate-400';
                const acciones = s.estado === 'Pendiente' ? `
                    <div class="flex gap-1.5 mt-2">
                        <button onclick="resolverSolicitudM6(${s.id_solicitud}, 'aceptada')" class="flex-1 py-1 text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white rounded font-medium">Aceptar</button>
                        <button onclick="resolverSolicitudM6(${s.id_solicitud}, 'rechazada')" class="flex-1 py-1 text-[10px] bg-rose-600 hover:bg-rose-500 text-white rounded font-medium">Rechazar</button>
                        <button onclick="cancelarSolicitudM6(${s.id_solicitud})" class="px-2 py-1 text-[10px] bg-slate-700 hover:bg-slate-600 text-slate-300 rounded font-medium">Cancelar</button>
                    </div>` : '';
                return `<div class="p-3 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1 text-xs">
                    <div class="flex justify-between items-center">
                        <span class="font-semibold text-slate-200">Solicitud #${s.id_solicitud}</span>
                        <span class="px-2 py-0.5 text-[10px] font-semibold border rounded-full ${badge}">${s.estado}</span>
                    </div>
                    <div class="text-slate-400">Tipo: <span class="text-slate-300">${s.tipo}</span> | Prioridad: <span class="text-slate-300">${s.prioridad}</span></div>
                    ${s.sector ? `<div class="text-slate-400">Sector: <span class="text-indigo-300">${s.sector}</span></div>` : ''}
                    ${s.cama ? `<div class="text-emerald-400">Cama: ${s.cama} | Hab: ${s.habitacion || '-'}</div>` : ''}
                    ${s.motivo_rechazo ? `<div class="text-rose-400">Rechazo: ${s.motivo_rechazo}</div>` : ''}
                    ${acciones}
                </div>`;
            }).join('');
        }

        async function resolverSolicitudM6(idSolicitud, decision) {
            const url = `/api/v1/solicitudes-cama/${idSolicitud}/resolver`;
            const payload = decision === 'aceptada'
                ? { decision, cama: 'Cama 4', habitacion: 'Hab 201' }
                : { decision, motivo_rechazo: 'Sin disponibilidad en el sector solicitado.' };
            logToConsole(`POST ${url} — decision: "${decision}"`, 'sent');
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${devToken}` },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`200 OK — Solicitud #${idSolicitud} ${decision}. ${decision === 'aceptada' ? 'Cama 4 / Hab 201 asignada.' : ''}`, 'success');
                    await cargarSolicitudesM6();
                } else { logToConsole(`${res.status} Error: ${JSON.stringify(data.detail)}`, 'error'); }
            } catch (e) { logToConsole(`Error: ${e.message}`, 'error'); }
        }

        async function cancelarSolicitudM6(idSolicitud) {
            const url = `/api/v1/solicitudes-cama/${idSolicitud}/cancelar`;
            logToConsole(`POST ${url} — Cancelar solicitud #${idSolicitud}`, 'sent');
            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${devToken}` }
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`200 OK — Solicitud #${idSolicitud} cancelada.`, 'success');
                    await cargarSolicitudesM6();
                } else { logToConsole(`${res.status} Error: ${JSON.stringify(data.detail)}`, 'error'); }
            } catch (e) { logToConsole(`Error: ${e.message}`, 'error'); }
        }

        async function simularIngresoM6() {
            const idPaciente = parseInt(document.getElementById('m6-id-paciente').value) || m6PacienteId;
            const idEpField = document.getElementById('m6-cb-id-episodio').value;
            const sector = document.getElementById('m6-cb-sector').value || 'UTI';
            const habitacion = document.getElementById('m6-cb-habitacion').value || null;
            const cama = document.getElementById('m6-cb-cama').value;
            if (!cama) { alert('Ingresa el número de cama.'); return; }
            const payload = {
                id_paciente: idPaciente,
                sector,
                cama,
                fecha_ingreso: new Date().toISOString(),
                medico_solicitante: 'Dr. Dev (Simulacion M6)',
            };
            if (habitacion) payload.habitacion = habitacion;
            if (idEpField) payload.id_episodio = parseInt(idEpField);
            logToConsole(`POST /api/v1/internacion/ingreso — Payload: ${JSON.stringify(payload)}`, 'sent');
            try {
                const res = await fetch('/api/v1/internacion/ingreso', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${devToken}` },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    logToConsole(`201 OK — Ingreso registrado. ${JSON.stringify(data.data)}`, 'success');
                    if (m6EpisodioId) await cargarSolicitudesM6();
                } else { logToConsole(`${res.status} Error: ${JSON.stringify(data.detail || data)}`, 'error'); }
            } catch (e) { logToConsole(`Error: ${e.message}`, 'error'); }
        }

        // Init page
        window.onload = async () => {
            await authenticate();
        };
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
