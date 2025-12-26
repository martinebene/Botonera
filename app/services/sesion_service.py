from typing import Optional
from datetime import datetime
import os

from app.models.sesion import Sesion

# Sesión actual en memoria (puede ser None si no hay sesión abierta ni creada)
CURRENT_SESION: Optional[Sesion] = None

# Archivo de log
LOG_FILE = "sesiones_log.txt"


def abrir_sesion(numero_sesion: int) -> Sesion:
    """
    Crea una nueva Sesion en memoria.

    Reglas de negocio:
    - Solo puede haber UNA sesión abierta a la vez.
    - Si ya hay una sesión abierta -> KeyError("ya_hay_abierta").
    - Si no hay sesión abierta:
        * crea Sesion(numero_sesion)
        * la deja como CURRENT_SESION
        * la devuelve
    """
    global CURRENT_SESION

    if CURRENT_SESION is not None and CURRENT_SESION.abierta:
        # Ya hay una sesión abierta, no se puede abrir otra
        raise KeyError("ya_hay_abierta")

    # Creamos una nueva sesión
    CURRENT_SESION = Sesion(numero_sesion=numero_sesion)
    return CURRENT_SESION


def cerrar_sesion() -> Sesion:
    """
    Cierra la sesión actual.

    Reglas:
    - Si no hay ninguna sesión (CURRENT_SESION es None) -> KeyError("no_hay_sesion")
    - Si la sesión ya estaba cerrada -> KeyError("ya_cerrada")
    - Si todo OK:
        * marca hora_fin
        * escribe en el log: "se abrio sesion nro X, a la hora Y, y se cerro a la hora Z"
        * deja CURRENT_SESION = None (ya no hay sesión activa)
    """
    global CURRENT_SESION

    if CURRENT_SESION is None:
        # Nunca se abrió una sesión o ya se limpió
        raise KeyError("no_hay_sesion")

    sesion = CURRENT_SESION

    if not sesion.abierta:
        # Por lógica normal no deberíamos llegar acá si limpiamos al cerrar,
        # pero lo dejamos por robustez
        raise KeyError("ya_cerrada")

    # Tomamos la hora de inicio antes de cerrar
    hora_inicio_str = sesion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")

    # Cerramos la sesión (pone hora_fin)
    sesion.cerrar()
    hora_fin_str = sesion.hora_fin.strftime("%Y-%m-%d %H:%M:%S") if sesion.hora_fin else "?"

    # Armamos la línea de log EXACTAMENTE como definiste
    linea = (
        f"se abrio sesion nro {sesion.numero_sesion}, "
        f"a la hora {hora_inicio_str}, "
        f"y se cerro a la hora {hora_fin_str}"
    )

    # Append al archivo de log
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linea + "\n")

    # Dejamos de tener sesión actual
    CURRENT_SESION = None

    return sesion


def obtener_sesion_actual() -> Optional[Sesion]:
    """
    Devuelve la sesión actual (puede ser None si no hay).
    """
    return CURRENT_SESION
