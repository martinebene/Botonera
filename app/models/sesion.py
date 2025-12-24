from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Sesion:
    """
    Clase de dominio pura, sin base de datos.

    Sesion:
    + id: Integer
    + numeroSesion: Integer
    + abierta: Boolean
    + horaInicio: TimeStamp
    + horaFin: TimeStamp
    + listaDeVotaciones[ ]: List Votacion   (todavía no implementadas)
    + listaDeDebates[ ]: List Debate
    + listaDeConcejales[ ]: List Concejal
    """

    id: int
    numero_sesion: int
    abierta: bool = True
    hora_inicio: datetime = field(default_factory=datetime.now)
    hora_fin: Optional[datetime] = None

    votaciones: List[dict] = field(default_factory=list)
    debates: List[dict] = field(default_factory=list)
    concejales: List[dict] = field(default_factory=list)

    def cerrar(self) -> None:
        """Marca la sesión como cerrada y registra la hora de fin."""
        self.abierta = False
        self.hora_fin = datetime.now()

    def to_dict(self) -> dict:
        """Convierte la sesión a un diccionario simple (para JSON)."""
        return {
            "id": self.id,
            "numero_sesion": self.numero_sesion,
            "abierta": self.abierta,
            "hora_inicio": self.hora_inicio.isoformat() if self.hora_inicio else None,
            "hora_fin": self.hora_fin.isoformat() if self.hora_fin else None,
            "votaciones": self.votaciones,
            "debates": self.debates,
            "concejales": self.concejales,
        }
