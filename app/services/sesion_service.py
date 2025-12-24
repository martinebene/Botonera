from typing import List, Optional
from datetime import datetime
import os

from app.models.sesion import Sesion

# Estado global en memoria
SESIONES: List[Sesion] = []
NEXT_ID: int = 1

# Archivo de log
LOG_FILE = "sesiones_log.txt"


def abrir_sesion(numero_sesion: int) -> Sesion:
    """
    Crea una nueva Sesion en memoria.

    - Usa NEXT_ID como id autoincremental.
    - Marca abierta=True y hora_inicio=ahora.
    - NO escribe en el log todavía (solo al cerrar).
    """
    global NEXT_ID

    sesion = Sesion(id=NEXT_ID, numero_sesion=numero_sesion)
    SESIONES.append(sesion)
    NEXT_ID += 1
    return sesion


def _buscar_sesion_por_id(sesion_id: int) -> Optional[Sesion]:
    """Busca una sesión por id en la lista SESIONES."""
    for s in SESIONES:
        if s.id == sesion_id:
            return s
    return None


def cerrar_sesion(sesion_id: int) -> Sesion:
    """
    Cierra una sesión existente.

    - Si no existe -> KeyError("no_encontrada")
    - Si ya estaba cerrada -> KeyError("ya_cerrada")
    - Si todo OK:
        * marca hora_fin
        * escribe una línea en el log:
          "se abrio sesion nro X, a la hora Y, y se cerro a la hora Z"
    """
    sesion = _buscar_sesion_por_id(sesion_id)
    if sesion is None:
        raise KeyError("no_encontrada")

    if not sesion.abierta:
        raise KeyError("ya_cerrada")

    # Guardamos la hora de inicio para el log
    hora_inicio_str = sesion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")

    # Cerramos y generamos hora_fin
    sesion.cerrar()
    hora_fin_str = sesion.hora_fin.strftime("%Y-%m-%d %H:%M:%S") if sesion.hora_fin else "?"

    # Escribimos en el log (append)
    linea = (
        f"se abrio sesion nro {sesion.numero_sesion}, "
        f"a la hora {hora_inicio_str}, "
        f"y se cerro a la hora {hora_fin_str}"
    )

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linea + "\\n")

    return sesion


def listar_sesiones() -> List[Sesion]:
    """Devuelve todas las sesiones en memoria."""
    return SESIONES
