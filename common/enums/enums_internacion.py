from enum import Enum


class PrioridadInternacion(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    EMERGENCIA = "Emergencia"


class SectorSolicitado(str, Enum):
    UTI = "UTI"
    SALA_COMUN = "Sala_Comun"
    GUARDIA_OBSERVACION = "Guardia_Observacion"
