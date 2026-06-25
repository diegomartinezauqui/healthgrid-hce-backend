from enum import Enum

class TipoEstudio(str, Enum):
    LABORATORIO = "Laboratorio"
    IMAGEN = "Imagen"
    ANATOMIA_PATOLOGICA = "Anatomia_Patologica"


class PrioridadOrden(str, Enum):
    NORMAL = "Normal"
    URGENTE = "Urgente"
    EMERGENCIA = "Emergencia"


class SubtipoEstudio(str, Enum):
    ECOGRAFIA = "ECOGRAFY"
    RADIOLOGIA = "RADIOLOGY"
    TOMOGRAFIA = "TOMOGRAPHY"
    RESONANCIA = "RESONANCE"
    MAMOGRAFIA = "MAMMOGRAPHY"
    DENSITOMETRIA = "DENSITOMETRY"
    ECODOPPLER = "ECODOPPLER"
    ENDOSCOPIA = "ENDOSCOPY"
