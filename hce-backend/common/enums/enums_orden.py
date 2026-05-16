from enum import Enum

class TipoEstudio(str, Enum):
    LABORATORIO = "Laboratorio"
    IMAGEN = "Imagen"
    ANATOMIA_PATOLOGICA = "Anatomia_Patologica"


class PrioridadOrden(str, Enum):
    NORMAL = "Normal"
    URGENTE = "Urgente"
    EMERGENCIA = "Emergencia"


class TipoAlertaClinica(str, Enum):
    CONTRAINDICACION_ABSOLUTA = "CONTRAINDICACION_ABSOLUTA"
    ALERGIA = "ALERGIA"
    RIESGO_SANGRADO = "RIESGO_SANGRADO"
    EMBARAZO = "EMBARAZO"
