from datetime import datetime
from typing import List, Optional, Dict, Any


class Sesion:
    """
    Clase de dominio pura, sin base de datos.

    Sesion:
    + numeroSesion: Integer
    + abierta: Boolean
    + horaInicio: TimeStamp
    + horaFin: TimeStamp
    + listaDeVotaciones[ ]: List Votacion   (todavía no implementadas)
    + listaDeDebates[ ]: List Debate
    + listaDeConcejales[ ]: List Concejal
    """

    def __init__(self, numero_sesion: int) -> None:
        # Atributos principales
        self.numero_sesion: int = numero_sesion
        self.abierta: bool = True
        self.hora_inicio: datetime = datetime.now()
        self.hora_fin: Optional[datetime] = None

        # Listas de trabajo (por ahora dicts, después pueden ser objetos)
        self.votaciones: List[Dict[str, Any]] = []
        self.debates: List[Dict[str, Any]] = []
        self.concejales: List[Dict[str, Any]] = []

    def cerrar(self) -> None:
        """
        Marca la sesión como cerrada y registra la hora de fin.
        """
        self.abierta = False
        self.hora_fin = datetime.now()

    def to_dict(self) -> dict:
        """
        Convierte la sesión a un diccionario simple (para JSON).
        """
        return {
            "numero_sesion": self.numero_sesion,
            "abierta": self.abierta,
            "hora_inicio": self.hora_inicio.isoformat() if self.hora_inicio else None,
            "hora_fin": self.hora_fin.isoformat() if self.hora_fin else None,
            "votaciones": self.votaciones,
            "debates": self.debates,
            "concejales": self.concejales,
        }
