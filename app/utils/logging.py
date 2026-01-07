
"""
Logger interno simple con 3 niveles y 3 archivos.

Ahora el directorio de logs se toma desde:
    settings.log_dir   (string)

Ejemplo:
    settings.log_dir = "logs"

Archivos generados:
    logs/app.log.1   -> nivel 1 (1, 2 y 3)
    logs/app.log.2   -> nivel 2 (2 y 3)
    logs/app.log.3   -> nivel 3 (solo 3)
"""

from __future__ import annotations

import os
from datetime import datetime
from threading import Lock
from typing import Final

# Ajustar SOLO este import si tu settings vive en otro módulo módulo
from app.config import settings


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

LOG_MIN_LEVEL: Final[int] = 1
LOG_MAX_LEVEL: Final[int] = 3

# Nombre base de los archivos de log (fijo)
LOG_BASE_NAME: Final[str] = "app.log"

# Lock tipo mutex para escritura concurrente
_lock = Lock()


# ---------------------------------------------------------------------------
# Funciones internas (helpers)
# ---------------------------------------------------------------------------

def _build_log_paths(log_dir: str) -> tuple[str, str, str]:
    """
    Construye las rutas completas de los 3 archivos de log
    a partir del directorio configurado.

    Ejemplo:
        log_dir = "logs"

    Devuelve:
        (
            "logs/app.log.1",
            "logs/app.log.2",
            "logs/app.log.3"
        )
    """
    path_1 = os.path.join(log_dir, f"{LOG_BASE_NAME}.1")
    path_2 = os.path.join(log_dir, f"{LOG_BASE_NAME}.2")
    path_3 = os.path.join(log_dir, f"{LOG_BASE_NAME}.3")

    return path_1, path_2, path_3


def _ensure_dir_exists(path: str) -> None:
    """
    Garantiza que el directorio donde se va a escribir exista.

    Si no existe, lo crea.
    Si ya existe, no hace nada.
    """
    os.makedirs(path, exist_ok=True)


def _format_line(tag: str, level: int, message: str) -> str:
    """
    Arma una línea de log con formato fijo.

    Formato:
        YYYY-MM-DD HH:MM:SS.mmm | L<level> | <tag> | <mensaje>
    """

    # Timestamp local con milisegundos
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    # Defensa contra None y basura de espacios
    safe_tag = (tag or "").strip()
    safe_message = (message or "").rstrip("\n")

    return f"{timestamp} | L{level} | {safe_tag} | {safe_message}\n"


# ---------------------------------------------------------------------------
# FUNCIÓN PÚBLICA
# ---------------------------------------------------------------------------

def log_internal(tag: str, level: int, message: str) -> None:
    """
    Logger interno del sistema.

    Parámetros:
        tag     -> identificador del subsistema ("SESION", "VOTO", etc.)
        level   -> 1 (detalle), 2 (normal), 3 (importante)
        message -> mensaje libre

    Escritura:
        level 1 -> app.log.1
        level 2 -> app.log.1 + app.log.2
        level 3 -> app.log.1 + app.log.2 + app.log.3
    """

    # ---------------------------------------------------------------------
    # Validación del nivel
    # ---------------------------------------------------------------------

    if not isinstance(level, int) or not (LOG_MIN_LEVEL <= level <= LOG_MAX_LEVEL):
        raise ValueError(f"Nivel de log inválido: {level}. Debe ser 1, 2 o 3.")

    # ---------------------------------------------------------------------
    # Obtener el directorio de logs desde settings
    # ---------------------------------------------------------------------

    log_dir = getattr(settings, "log_dir", None)
    
    if not log_dir or not isinstance(log_dir, str):
        raise RuntimeError("settings.log_dir no está definido o no es un string.")

    # ---------------------------------------------------------------------
    # Asegurar que el directorio exista
    # ---------------------------------------------------------------------

    _ensure_dir_exists(log_dir)

    # ---------------------------------------------------------------------
    # Construir rutas de los archivos
    # ---------------------------------------------------------------------

    log_1, log_2, log_3 = _build_log_paths(log_dir)

    # ---------------------------------------------------------------------
    # Formatear línea
    # ---------------------------------------------------------------------

    line = _format_line(tag, level, message)

    # ---------------------------------------------------------------------
    # Escritura protegida (mutex)
    # ---------------------------------------------------------------------

    with _lock:

        # Nivel 1: siempre
        with open(log_1, "a", encoding="utf-8") as f:
            f.write(line)

        # Nivel 2 y 3
        if level >= 2:
            with open(log_2, "a", encoding="utf-8") as f:
                f.write(line)

        # Solo nivel 3
        if level >= 3:
            with open(log_3, "a", encoding="utf-8") as f:
                f.write(line)
