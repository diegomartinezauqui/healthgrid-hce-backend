"""
Provisiona el bus de eventos de HCE en el Core (M10).

Crea (vía el Core):
  1. Cola de responses `hce.responses`  (para recibir respuestas a nuestras requests).
  2. Cola de requests  `hce.requests`   (para recibir requests de otros módulos).
  3. Los tipos de evento que HCE posee / espera.
  4. Los bindings evento → cola.

Imprime los IDs de evento para compartir con los otros equipos.

Requisitos:
  - ENABLE_CORE_BUS=True y credenciales del Core en el entorno:
    CORE_SERVICE_EMAIL, CORE_SERVICE_PASSWORD, CORE_API_URL, RABBITMQ_*.

Uso (desde `hce-backend`):
    python scripts/setup_core_bus.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402

from app.config import settings  # noqa: E402
from app.integrations import core_bus  # noqa: E402

BASE = settings.HCE_QUEUE_BASE

# Eventos que HCE va a escuchar (in) o publicar (out).
EVENTOS_DESEADOS = [
    {"name": "hce.internacion.solicitud_resuelta", "desc": "M6 resolvió la solicitud de cama (aprobada/rechazada)", "dir": "in", "source": "hce"},
    {"name": "laboratorio.resultado_listo", "desc": "Publicado por Laboratorio cuando un resultado de análisis queda finalizado.", "dir": "in", "source": "laboratorio"},
    {"name": "SOLICITUD_RESUELTA", "desc": "Evento publicado por Modulo 6 cuando una solicitud de cama es aprobada o rechazada", "dir": "in", "source": "internacion"},
]


async def main() -> None:
    if not settings.CORE_SERVICE_EMAIL or not settings.CORE_SERVICE_PASSWORD:
        print("❌ Faltan CORE_SERVICE_EMAIL / CORE_SERVICE_PASSWORD en el entorno.")
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        print(f"Core: {settings.CORE_API_URL}")

        # 1) Crear cola de HCE
        for tipo in ("responses",):
            try:
                r = await core_bus.create_queue(client, BASE, tipo)
                print(f"[OK] Cola {BASE}.{tipo}: {r}")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Cola {BASE}.{tipo}: {exc}")

        # 2) Obtener todos los tipos de eventos registrados en el Core para no duplicar y mapear IDs
        print("\n-- Obteniendo eventos registrados en el Core --")
        eventos_core = []
        page = 1
        headers = {}
        # Obtener token para consultar eventos
        try:
            resp = await client.post(
                f"{settings.CORE_API_URL}/auth/login",
                json={"email": settings.CORE_SERVICE_EMAIL, "password": settings.CORE_SERVICE_PASSWORD}
            )
            if resp.status_code == 200:
                token = resp.json().get("token") or resp.json().get("access_token")
                headers = {"Authorization": f"Bearer {token}"}
        except Exception as exc:
            print(f"[WARNING] No se pudo autenticar para consultar tipos de eventos: {exc}")

        if headers:
            try:
                while True:
                    resp = await client.get(f"{settings.CORE_API_URL}/events/types?page={page}&pageSize=10", headers=headers)
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    events = data.get("data", [])
                    if not events:
                        break
                    eventos_core.extend(events)
                    page += 1
                    if len(eventos_core) >= data.get("total", 0):
                        break
                print(f"Total eventos en el Core: {len(eventos_core)}")
            except Exception as exc:
                print(f"[WARNING] Error obteniendo tipos de eventos: {exc}")

        # Mapa de nombre a ID de los eventos del Core
        mapa_eventos = {t["name"]: t["id"] for t in eventos_core if "name" in t and "id" in t}

        # 3) Resolver cada evento deseado
        print("\n-- Procesando Bindings y Eventos --")
        for ev in EVENTOS_DESEADOS:
            event_id = mapa_eventos.get(ev["name"])
            
            if not event_id:
                # Si no existe en el Core, intentar crearlo (solo si somos el owner/source)
                try:
                    creado = await core_bus.create_event(client, ev["name"], ev["desc"], ev["source"])
                    event_id = creado.get("id")
                    print(f"[NUEVO] Evento {ev['name']} creado con id={event_id}")
                except Exception as exc:
                    print(f"[ERROR] No se pudo crear el evento {ev['name']}: {exc}")
            else:
                print(f"[EXISTENTE] Evento {ev['name']} ya existe con id={event_id}")

            # 4) Bindear si es de entrada (in)
            if ev["dir"] == "in" and event_id:
                try:
                    res_bind = await core_bus.create_binding(client, event_id, f"{BASE}.responses")
                    print(f"    -> [OK] Bindeado a {BASE}.responses -> {res_bind.get('routing_key') or res_bind}")
                except Exception as exc:
                    print(f"    -> [ERROR] Al bindear {ev['name']}: {exc}")

    print("\nSetup finalizado.")


if __name__ == "__main__":
    asyncio.run(main())
