from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from collections import deque

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
    - en_uso_de_palabra: concejal en uso de la palabra si lo hubiese
    - pedidos_de_uso_de_palabra: cola de concejales que pidieron la palabra
    """

    def __init__(self, numero_sesion: int) -> None:
        self.numero_sesion = numero_sesion
        self.abierta: bool = True
        self.hora_inicio: datetime = datetime.now()
        self.hora_fin: Optional[datetime] = None
        self.presentes: Optional[int]=None
        self.quorum: Optional[int]=None
        self.disposicion_bancas:Optional[str]=None
        self.concejales: List[Concejal] = []
        self.votaciones: List[Votacion] = []
        self.pedidos_uso_de_palabra = deque()   # deque[Concejal]
        self.en_uso_de_palabra: Optional[Concejal] = None 


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
            "cantidad_concejales": len(self.concejales),
            "cantidad_presentes": sum(1 for c in self.concejales if c.presente),
            "quorum":self.quorum,
            "disposicion_bancas":self.disposicion_bancas,
            "concejales": [c.to_dict() for c in self.concejales],
            "votaciones": [v.to_dict() for v in self.votaciones],
            "pedidos_uso_de_palabra":[p.to_dict() for p in self.pedidos_uso_de_palabra],
            "en_uso_de_palabra":self.en_uso_de_palabra
        }
