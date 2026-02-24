from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum

from app.models.concejal import Concejal


class ValorVoto(Enum):
    POSITIVO = "Positivo"
    NEGATIVO = "Negativo"
    ABSTENCION = "Abstención"

class Voto:
    """
    Representa el voto de un concejal en una votación.
    """

    _next_id: int = 1

    def __init__(
        self,
        concejal: Optional[Concejal],
        valor_voto: ValorVoto,
        hora_emision: Optional[datetime] = None,
        id: Optional[int] = None,
    ) -> None:
        # ID interno en memoria, auto-incremental si no se pasa
        if id is None:
            self.id = Voto._next_id
            Voto._next_id += 1
        else:
            self.id = id

        self.concejal = concejal
        if not isinstance(valor_voto, ValorVoto):
            raise ValueError("valor_voto inválido")
        self.valor_voto = valor_voto
        self.hora_emision = hora_emision or datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "concejal": self.concejal.to_dict() if self.concejal else None,
            "valor_voto": self.valor_voto.value,
            "hora_emision": self.hora_emision.isoformat(),
        }
