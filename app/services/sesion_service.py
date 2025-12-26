from typing import Optional
from datetime import datetime

from app.models.sesion import Sesion
from app.services.concejal_service import cargar_concejales_desde_archivo
from app.config import settings

# Sesión actual en memoria (única)
CURRENT_SESION: Optional[Sesion] = None


def abrir_sesion(numero_sesion: int) -> Sesion:
    """
    Crea una nueva Sesion en memoria.

    Reglas:
    - Solo puede haber UNA sesión abierta a la vez.
    - Si ya hay una sesión abierta -> KeyError("ya_hay_abierta").
    - Se deben cargar concejales desde el archivo config.
    - Si no hay concejales -> KeyError("sin_concejales").
    """

    global CURRENT_SESION

    if CURRENT_SESION is not None and CURRENT_SESION.abierta:
        raise KeyError("ya_hay_abierta")

    # Intentamos cargar los concejales ANTES de crear la sesión
    try:
        concejales = cargar_concejales_desde_archivo(settings.concejales_file)
    except FileNotFoundError:
        raise KeyError("archivo_concejales_no_encontrado")

    if not concejales or len(concejales) == 0:
        raise KeyError("sin_concejales")

    # Si llegamos hasta acá, concejales es válido → creamos Sesion
    sesion = Sesion(numero_sesion=numero_sesion)
    sesion.concejales = concejales

    CURRENT_SESION = sesion
    return CURRENT_SESION


def cerrar_sesion() -> Sesion:
    """
    Cierra la sesión actual.

    Reglas:
    - Si no hay sesión -> KeyError("no_hay_sesion")
    - Si ya está cerrada -> KeyError("ya_cerrada")
    - Registra en el log:
        se abrio sesion nro X, a la hora Y, y se cerro a la hora Z
    """

    global CURRENT_SESION

    if CURRENT_SESION is None:
        raise KeyError("no_hay_sesion")

    sesion = CURRENT_SESION

    if not sesion.abierta:
        raise KeyError("ya_cerrada")

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

    CURRENT_SESION = None
    return sesion


def obtener_sesion_actual() -> Optional[Sesion]:
    """
    Devuelve la sesión actual (o None si no hay).
    """
    return CURRENT_SESION
