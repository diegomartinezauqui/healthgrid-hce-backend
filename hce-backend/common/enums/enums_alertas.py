"""Enums de alertas clínicas del paciente."""

from enum import Enum

# --------Deprecado---------
class TipoAlertaFarmacologica(str, Enum):
    ALERGIA_MEDICAMENTOSA = "ALERGIA_MEDICAMENTOSA"
    INSUFICIENCIA_RENAL = "INSUFICIENCIA_RENAL"
    INSUFICIENCIA_HEPATICA = "INSUFICIENCIA_HEPATICA"
    EMBARAZO = "EMBARAZO"
# --------Fin deprecado---------

class TipoConsideracion(str, Enum):
    """Tipo de consideración/alerta clínica del paciente."""
    ALERGIA = "Alergia"
    DISPOSITIVO_IMPLANTADO = "Dispositivo_Implantado"
    CONDICION_CRITICA = "Condicion_Critica"
    RIESGO_INFECCIOSO = "Riesgo_Infeccioso"
    CONTRAINDICACION = "Contraindicacion"


class SeveridadAlerta(str, Enum):
    """Nivel de severidad de la alerta."""
    LEVE = "Leve"
    MODERADA = "Moderada"
    SEVERA = "Severa"
    CRITICA = "Critica"


class EstadoAlerta(str, Enum):
    """Estado del ciclo de vida de la alerta."""
    ACTIVA = "Activa"
    RESUELTA = "Resuelta"
