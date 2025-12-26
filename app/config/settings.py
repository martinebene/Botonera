import json
import os
from typing import Any, Dict


class Settings:
    """
    Configuración global obligatoria de la aplicación.
    - NO tiene valores por defecto.
    - Si falta config.json → error.
    - Si faltan claves requeridas → error.
    """

    REQUIRED_KEYS = [
        "concejales_file",
        "log_file"
    ]

    def __init__(self, config_path: str = "config.json") -> None:
        self.config_path = config_path
        self._raw: Dict[str, Any] = {}

        self.load()
        self.validate()

        # Asignamos los atributos obligatorios
        self.concejales_file = self._raw["concejales_file"]
        self.log_file = self._raw["log_file"]

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


# Instancia única, global
settings = Settings()
