from enum import Enum


class EstadoReceta(str, Enum):
    ACTIVA = "Activa"
    SUSPENDIDA = "Suspendida"
    DISPENSADA = "Dispensada"
