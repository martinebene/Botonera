from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.models.concejal import Concejal
from app.models.votacion import Votacion


class Sesion:
    """
    Representa una sesión del Concejo.

    - numero_sesion: identificador público (lo que maneja el operador).
    - abierta: indica si la sesión sigue activa.
    - hora_inicio / hora_fin: timestamps.
    - concejales: lista de concejales asociados.
    - votaciones: lista de votaciones realizadas en la sesión.
    """

    def __init__(self, numero_sesion: int) -> None:
        self.numero_sesion = numero_sesion
        self.abierta: bool = True
        self.hora_inicio: datetime = datetime.now()
        self.hora_fin: Optional[datetime] = None

        self.concejales: List[Concejal] = []
        self.votaciones: List[Votacion] = []

    def cerrar(self) -> None:
        """Cierra la sesión y fija la hora de fin."""
        if not self.abierta:
            return
        self.abierta = False
        self.hora_fin = datetime.now()

    def to_dict(self) -> dict:
        return {
            "numero_sesion": self.numero_sesion,
            "abierta": self.abierta,
            "hora_inicio": self.hora_inicio.isoformat(),
            "hora_fin": self.hora_fin.isoformat() if self.hora_fin else None,
            "concejales": [c.to_dict() for c in self.concejales],
            "votaciones": [v.to_dict() for v in self.votaciones],
        }
