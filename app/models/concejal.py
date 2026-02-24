from typing import Optional, Dict, Any
import time

class Concejal:
    """
    Clase de dominio para representar un concejal.

    Atributos:
    - dni: str
    - nombre: str
    - apellido: str
    - bloque: str
    - presente: bool
    - banca: int
    - dispositivo_votacion: Optional[str]
    """

    def __init__(
        self,
        dni: str,
        nombre: str,
        apellido: str,
        bloque: str,
        presente: bool,
        banca: int,
        dispositivo_votacion: Optional[str] = None,
    ) -> None:

        self.dni = dni
        self.nombre = nombre
        self.apellido = apellido
        self.bloque = bloque
        self.presente = presente
        self.banca = banca
        self._mostrar_test_hasta = 0.0  # time.monotonic() hasta cuándo mostrar
        self.dispositivo_votacion = dispositivo_votacion

    def __repr__(self)->str:
        return self.print_corto()

    def print_corto(self) -> str:
        """
        Convierte el concejal en un diccionario para JSON.
        """
        return self.nombre+" "+self.apellido+" (banca Nro:"+str(self.banca)+")"

    def activar_test_temporal(self, duracion_s: float = 1.0) -> None:
        ahora = time.monotonic()
        duracion = max(0.0, float(duracion_s))
        # si ya estaba activo, extendemos; si no, lo activamos
        self._mostrar_test_hasta = max(self._mostrar_test_hasta, ahora + duracion)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el concejal en un diccionario para JSON .
        """
        return {
            "dni": self.dni,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "bloque": self.bloque,
            "presente": self.presente,
            "banca": self.banca,
            "dispositivo_votacion": self.dispositivo_votacion,
            "mostrar_test": (time.monotonic() < self._mostrar_test_hasta),
        }
