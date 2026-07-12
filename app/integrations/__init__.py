"""
Clients de salida hacia otros módulos del ecosistema Health Grid.

Todos respetan `settings.INTEGRATION_MODE`:
  - "mock" (default): loguean la intención y devuelven una respuesta canónica
    sin realizar HTTP real. Permite demostrar el contrato sin depender de los
    servidores live de los otros grupos.
  - "live": realizan la llamada HTTP real.
"""
