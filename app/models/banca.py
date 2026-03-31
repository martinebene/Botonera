from __future__ import annotations

from app.models.concejal import Concejal
from app.models.voto import ValorVoto


class Banca:
    """
    Representa el voto de un concejal en una votación.
    """
    numero_banca:int
    nombre_concejal:str | None
    en_uso_palabra: bool
    presente: bool
    test:bool
    voto: ValorVoto | None


    def __init__(self, concejal: Concejal) -> None:

        self.numero_banca = concejal.banca
        self.nombre_concejal = concejal.print_corto()
        self.en_uso_palabra = False
        self.presente = concejal.presente
        self.test = False
        self.voto = None  # ValorVoto | None

    def to_dict(self) -> dict:
        return {
            "numero_banca": self.numero_banca,
            "nombre_concejal": self.nombre_concejal,
            "en_uso_palabra": self.en_uso_palabra,
            "presente": self.presente,
            "test": self.test,
            "voto": self.voto.name if self.voto else None,
        }
