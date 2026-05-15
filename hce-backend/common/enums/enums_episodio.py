from enum import Enum

class TipoEpisodio(str, Enum):
    CONSULTA_EXTERNA = "consulta-externa"
    INTERNACION = "internacion"
    GUARDIA = "guardia"
    CIRUGIA = "cirugia"


class EstadoEpisodio(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class TipoActoMedico(str, Enum):
    CONSULTA = "consulta"
    ESTUDIO_LABORATORIO = "estudio-laboratorio"
    ESTUDIO_IMAGEN = "estudio-imagen"
    PROCEDIMIENTO = "procedimiento"
    CIRUGIA = "cirugia"
    MEDICACION = "medicacion"
    DESCARTABLE = "descartable"