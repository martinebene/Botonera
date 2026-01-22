"""
Logger interno simple con 3 niveles.

Toma el directorio raíz desde:
    settings.log_dir   (string)

Por cada día (AAAA-MM-DD) crea un subdirectorio:
    <log_dir>/AAAA-MM-DD/

Y escribe en 3 archivos .txt con nombre:
    AAAA-MM-DD-1.txt   -> nivel 1 (1, 2 y 3)
    AAAA-MM-DD-2.txt   -> nivel 2 (2 y 3)
    AAAA-MM-DD-3.txt   -> nivel 3 (solo 3)
"""

from __future__ import annotations

import os
from datetime import datetime
from threading import Lock
from typing import Final
from collections import deque

from app.config import settings


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Niveles permitidos
LOG_MIN_LEVEL: Final[int] = 1
LOG_MAX_LEVEL: Final[int] = 3

# Tamaño del buffer circular en RAM para estados al frontend:
LOG_RAM_MAXLEN: Final[int] = 20

# Lock tipo mutex para escritura concurrente
_lock = Lock()

# Contador incremental de eventos (sirve para que el frontend no duplique líneas)
_log_seq: int = 0

# Buffer circular de últimos eventos en RAM
# Cada elemento será un dict:
#   {"seq": <int>, "line": <str>}
_log_ram_tail = deque(maxlen=LOG_RAM_MAXLEN)


# ---------------------------------------------------------------------------
# Funciones internas (helpers)
# ---------------------------------------------------------------------------

def _ensure_dir_exists(path: str) -> None:
    """
    Garantiza que el directorio exista.
    Si no existe, lo crea. Si ya existe, no hace nada.
    """
    os.makedirs(path, exist_ok=True)


def _today_str() -> str:
    """
    Devuelve la fecha local en formato AAAA-MM-DD.
    Ejemplo: '2026-01-08'
    """
    return datetime.now().strftime("%Y-%m-%d")


def _build_log_paths(log_root_dir: str, day_str: str) -> tuple[str, str, str, str]:
    """
    Construye:
      - el directorio del día: <log_root_dir>/<AAAA-MM-DD>/
      - los 3 archivos de log dentro de ese directorio:
            AAAA-MM-DD-1.txt
            AAAA-MM-DD-2.txt
            AAAA-MM-DD-3.txt

    Devuelve:
        (day_dir, path_1, path_2, path_3)
    """
    day_dir = os.path.join(log_root_dir, day_str)

    path_1 = os.path.join(day_dir, f"{day_str}-1.txt")
    path_2 = os.path.join(day_dir, f"{day_str}-2.txt")
    path_3 = os.path.join(day_dir, f"{day_str}-3.txt")

    return day_dir, path_1, path_2, path_3


def _format_line(tag: str, level: int, message: str) -> str:
    """
    Arma una línea de log con formato fijo.

    Formato:
        HH:MM:SS | L<level> | <tag> | <mensaje>
    """
    timestamp = datetime.now().strftime("%H:%M:%S")

    safe_tag = (tag or "").strip()
    safe_message = (message or "").rstrip("\n")

    return f"{timestamp} | L{level} | {safe_tag} | {safe_message}"


# ---------------------------------------------------------------------------
# FUNCIÓNES PÚBLICAS
# ---------------------------------------------------------------------------

def get_log_tail() -> list[dict]:
    """
    Devuelve una COPIA (lista) del buffer circular en RAM.

    Se devuelve lista (no deque) porque:
    - es JSON-friendly
    - evita exponer la deque interna
    """
    with _lock:
        return list(_log_ram_tail)


def log_internal(tag: str, level: int, message: str) -> None:
    """
    Logger interno del sistema.

    Parámetros:
        tag     -> identificador del subsistema ("SESION", "VOTO", etc.)
        level   -> 1 (detalle), 2 (normal), 3 (importante)
        message -> mensaje libre

    Escritura:
        level 1 -> archivo -1.txt
        level 2 -> archivos -1.txt y -2.txt
        level 3 -> archivos -1.txt, -2.txt y -3.txt

    Los archivos se escriben dentro del directorio del día:
        <settings.log_dir>/AAAA-MM-DD/
    """

    # Validación del nivel
    if not isinstance(level, int) or not (LOG_MIN_LEVEL <= level <= LOG_MAX_LEVEL):
        raise ValueError(f"Nivel de log inválido: {level}. Debe ser 1, 2 o 3.")

    # Obtener el directorio raíz de logs desde settings
    log_root_dir = getattr(settings, "log_dir", None)
    if not log_root_dir or not isinstance(log_root_dir, str):
        raise RuntimeError("settings.log_dir no está definido o no es un string.")

    # Fecha actual (para directorio y nombres de archivo)
    day_str = _today_str()

    # Construir rutas del día
    day_dir, log_1, log_2, log_3 = _build_log_paths(log_root_dir, day_str)

    # Asegurar que existan el root y el subdirectorio del día
    _ensure_dir_exists(log_root_dir)
    _ensure_dir_exists(day_dir)

    # Formatear línea (sin '\n')
    line_no_nl = _format_line(tag, level, message)

    global _log_seq
    # Escritura protegida (mutex)
    with _lock:

        _log_seq += 1
        _log_ram_tail.append({
            "seq": _log_seq,
            "line": line_no_nl,
        })

        # al escribir a archivos (agregamos '\n')
        line = line_no_nl + "\n"
        
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
