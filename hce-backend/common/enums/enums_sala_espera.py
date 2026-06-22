from enum import Enum


class EstadoSalaEspera(str, Enum):
    ESPERANDO = "Esperando"
    LLAMADO = "Llamado"
    ATENDIDO = "Atendido"
    AUSENTE = "Ausente"
    FINALIZADO = "Finalizado"
