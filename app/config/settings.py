import json
import os
from typing import Any, Dict
from app.version import VERSION


class Settings:
    """
    Configuración global obligatoria de la aplicación.
    - NO tiene valores por defecto.
    - Si falta config.json → error.
    - Si faltan claves requeridas → error.
    """

    REQUIRED_KEYS = [
        "concejales_file",
        "log_file",
        "log_dir",
        "quorum",
        "disposicion_bancas"
    ]

    def __init__(self, config_path: str = "config.json") -> None:
        self.config_path = config_path
        self._raw: Dict[str, Any] = {}

        self.load()
        self.validate()

        # Asignamos los atributos obligatorios
        self.concejales_file = self._raw["concejales_file"]
        self.log_file = self._raw["log_file"]
        self.log_dir = self._raw["log_dir"]
        self.quorum = self._raw["quorum"]
        self.disposicion_bancas = self._raw["disposicion_bancas"]
        self.version = VERSION

    def load(self) -> None:
        """Carga estricta del archivo de configuración."""

        if not os.path.exists(self.config_path):
            raise RuntimeError(
                f"ERROR: No se encontró el archivo de configuración requerido: '{self.config_path}'."
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._raw = json.load(f)
        except Exception as e:
            raise RuntimeError(
                f"ERROR: No se pudo leer '{self.config_path}': {e}"
            )

    def validate(self) -> None:
        """Verifica que todas las claves requeridas existan."""

        for key in self.REQUIRED_KEYS:
            if key not in self._raw:
                raise RuntimeError(
                    f"ERROR en configuración: falta la clave obligatoria '{key}' en {self.config_path}"
                )

    def to_dict(self) -> dict:
        return {
            "version": VERSION,
            "concejales_file": self.concejales_file,
            "log_file": self.log_file,
            "log_dir": self.log_dir,
            "quorum": self.quorum,
            "disposicion_bancas": self.disposicion_bancas,
        }

# Instancia única, global
settings = Settings()
