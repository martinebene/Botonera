from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.concejal import Concejal


class UsoDePalabra:
    """
    Representa el voto de un concejal en una votación.
    """

    _next_id: int = 1

    def __init__(
        self,
        concejal: Concejal,
        valor_voto: str,
        hora_emision: Optional[datetime] = None,
        id: Optional[int] = None,
    ) -> None:
        # ID interno en memoria, auto-incremental si no se pasa
        if id is None:
            self.id = UsoDePalabra._next_id
            UsoDePalabra._next_id += 1
        else:
            self.id = id

        self.concejal = concejal
        self.valor_voto = valor_voto
        self.hora_emision = hora_emision or datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "concejal": self.concejal.to_dict(),
            "valor_voto": self.valor_voto,
            "hora_emision": self.hora_emision.isoformat(),
        }
