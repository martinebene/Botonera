from typing import Optional, Dict, Any


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
        self.dispositivo_votacion = dispositivo_votacion

    def print_corto(self) -> str:
        """
        Convierte el concejal en un diccionario para JSON.
        """
        return self.nombre+" "+self.apellido+" (banca Nro:"+str(self.banca)+")"

    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el concejal en un diccionario para JSON.
        """
        return {
            "dni": self.dni,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "bloque": self.bloque,
            "presente": self.presente,
            "banca": self.banca,
            "dispositivo_votacion": self.dispositivo_votacion,
        }
