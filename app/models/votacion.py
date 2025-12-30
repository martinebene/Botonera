from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.models.voto import Voto


class Votacion:
    """
    Representa una votación dentro de una sesión.
    """

    _next_id: int = 1

    def __init__(
        self,
        numero: int,
        tipo: str,
        tema: str,
        id: Optional[int] = None,
    ) -> None:
        # ID interno en memoria, auto-incremental
        if id is None:
            self.id = Votacion._next_id
            Votacion._next_id += 1
        else:
            self.id = id

        self.numero = numero
        self.tipo = tipo
        self.tema = tema

        self.abierta: bool = True
        self.hora_inicio: datetime = datetime.now()
        self.hora_fin: Optional[datetime] = None

        self.votos: List[Voto] = []

    def registrar_voto(self, voto: Voto) -> None:
        """
        Agrega un voto a la votación.

        Reglas:
        - La votación debe estar abierta.
        - Solo un voto por concejal.
        """
        if not self.abierta:
            raise ValueError("votacion_cerrada")

        for v in self.votos:
            if v.concejal.dni == voto.concejal.dni:
                raise ValueError("concejal_ya_voto")

        self.votos.append(voto)

    def cerrar(self) -> None:
        """Cierra la votación y registra hora de fin."""
        if not self.abierta:
            return
        self.abierta = False
        self.hora_fin = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "numero": self.numero,
            "tipo": self.tipo,
            "tema": self.tema,
            "abierta": self.abierta,
            "hora_inicio": self.hora_inicio.isoformat(),
            "hora_fin": self.hora_fin.isoformat() if self.hora_fin else None,
            "votos": [v.to_dict() for v in self.votos],
        }
