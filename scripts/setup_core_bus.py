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

# Eventos que HCE va a manejar por el bus. `dir`: 'in' = escuchamos, 'out' = publicamos.
EVENTOS = [
    {"name": "hce.orden.creada",        "desc": "HCE creó una orden de estudio (M4/M5)", "dir": "out"},
    {"name": "hce.receta.creada",       "desc": "HCE emitió una receta (M3 Farmacia)",   "dir": "out"},
    {"name": "hce.internacion.solicitada", "desc": "HCE solicita internación (M6 Camas)", "dir": "out"},
    {"name": "hce.notificacion.obligatoria", "desc": "HCE notifica patología (Epidemiología)", "dir": "out"},
    {"name": "hce.episodio.cerrado",    "desc": "HCE cerró un episodio médico (M6/M7)",  "dir": "out"},
]


async def main() -> None:
    if not settings.CORE_SERVICE_EMAIL or not settings.CORE_SERVICE_PASSWORD:
        print("❌ Faltan CORE_SERVICE_EMAIL / CORE_SERVICE_PASSWORD en el entorno.")
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        print(f"Core: {settings.CORE_API_URL}")

        # 1) Colas
        for tipo in ("responses", "requests"):
            try:
                r = await core_bus.create_queue(client, BASE, tipo)
                print(f"[OK] Cola {BASE}.{tipo}: {r}")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Cola {BASE}.{tipo}: {exc}")

        # 2) Eventos + 3) bindings de los que escuchamos (dir=in) a nuestras colas
        print("\n-- Eventos --")
        for ev in EVENTOS:
            try:
                creado = await core_bus.create_event(client, ev["name"], ev["desc"], "hce")
                event_id = creado.get("id")
                print(f"[OK] Evento {ev['name']} -> id={event_id}  ({ev['dir']})")
                if ev["dir"] == "in" and event_id:
                     await core_bus.create_binding(client, event_id, f"{BASE}.responses")
                     print(f"   ↳ bindeado a {BASE}.responses")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Evento {ev['name']}: {exc}")

    print("\nSetup finalizado. Comparti los IDs de evento con los otros grupos "
          "y cargalos en la config (ej. CORE_EVENT_ORDEN_CREADA_ID).")


if __name__ == "__main__":
    asyncio.run(main())
