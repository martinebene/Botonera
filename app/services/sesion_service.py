from typing import Optional, List
from datetime import datetime

from app.models.sesion import Sesion
from app.models.concejal import Concejal
from app.services.concejal_service import cargar_concejales_desde_archivo
from app.config import settings


class SesionService:
    """
    Servicio de dominio para manejar la sesión del Concejo.

    - Mantiene una ÚNICA sesión en memoria (sesion_actual).
    - Abre/cierra sesión.
    - Registra el cierre en un archivo de log.
    """

    def __init__(self) -> None:
        self.sesion_actual: Optional[Sesion] = None

    def abrir_sesion(self, numero_sesion: int) -> Sesion:
        """
        Abre una nueva sesión.

        Reglas:
        - Si ya hay sesión abierta -> ValueError.
        - Debe existir un archivo de concejales válido.
        - Debe haber al menos un concejal cargado.
        """

        if self.sesion_actual is not None and self.sesion_actual.abierta:
            raise ValueError("Ya hay una sesión abierta. Debe cerrarla antes de abrir otra.")

        # Cargamos concejales ANTES de crear la sesión
        try:
            concejales: List[Concejal] = cargar_concejales_desde_archivo(settings.concejales_file)
        except FileNotFoundError:
            raise ValueError("No se encontró el archivo de concejales. No se puede abrir la sesión.")

        if not concejales:
            raise ValueError("La lista de concejales está vacía. No se puede abrir la sesión.")

        sesion = Sesion(numero_sesion=numero_sesion)
        sesion.concejales = concejales

        self.sesion_actual = sesion
        return sesion

    def cerrar_sesion(self) -> Sesion:
        """
        Cierra la sesión actual.

        Reglas:
        - Si no hay sesión -> ValueError("No hay ninguna sesión abierta.")
        - Si ya está cerrada -> ValueError("La sesión ya está cerrada.")
        - Registra en sesiones_log.txt:
          "se abrio sesion nro X, a la hora Y, y se cerro a la hora Z"
        """

        if self.sesion_actual is None:
            raise ValueError("No hay ninguna sesión abierta.")

        sesion = self.sesion_actual

        if not sesion.abierta:
            raise ValueError("La sesión ya está cerrada.")

        hora_inicio_str = sesion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")

        sesion.cerrar()
        hora_fin_str = sesion.hora_fin.strftime("%Y-%m-%d %H:%M:%S")

        linea = (
            f"se abrio sesion nro {sesion.numero_sesion}, "
            f"a la hora {hora_inicio_str}, "
            f"y se cerro a la hora {hora_fin_str}"
        )

        with open(settings.log_file, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

        # Dejamos la referencia, por si querés consultar la última sesión cerrada,
        # pero marcada como no abierta. Si preferís, podés poner self.sesion_actual = None.
        self.sesion_actual = None

        return sesion

    def obtener_sesion_actual(self) -> Optional[Sesion]:
        """Devuelve la sesión actual (o None si no hay)."""
        return self.sesion_actual


# Instancia única (singleton simple) a usar en toda la app
sesion_service = SesionService()
