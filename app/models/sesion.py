from datetime import datetime
from typing import List, Optional, Dict, Any

from app.models.concejal import Concejal


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
        self.numero_sesion: int = numero_sesion
        self.abierta: bool = True
        self.hora_inicio: datetime = datetime.now()
        self.hora_fin: Optional[datetime] = None

        # Por ahora las dejamos como listas vacías
        self.votaciones: List[Dict[str, Any]] = []
        self.debates: List[Dict[str, Any]] = []

        # Ahora sí: lista de objetos Concejal
        self.concejales: List[Concejal] = []

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
            # Serializamos los concejales llamando a to_dict() de cada uno
            "concejales": [c.to_dict() for c in self.concejales],
        }
