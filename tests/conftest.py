import json
import os
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIGURACION_TEMPORAL = tempfile.TemporaryDirectory()
with open(Path(CONFIGURACION_TEMPORAL.name) / "config.json", "w", encoding="utf-8") as archivo:
    json.dump(
        {
            "concejales_file": "concejales-ficticios.csv",
            "log_file": "logs-ficticios.log",
            "log_dir": "logs-ficticios",
            "quorum": 2,
            "disposicion_bancas": {"filas": []},
        },
        archivo,
    )

os.chdir(CONFIGURACION_TEMPORAL.name)
try:
    from app.config import settings
finally:
    os.chdir(REPO_ROOT)

from app.models.concejal import Concejal
from app.models.votacion import Votacion
from app.models.voto import Voto
from app.services import sesion_service as sesion_service_module
from app.services import votacion_service as votacion_service_module
from app.services.InfoPantallasService import info_pantallas_service
from app.utils import logging


@pytest.fixture
def concejales():
    def construir(total=3, presentes=3):
        return [
            Concejal(
                dni=str(indice + 1),
                nombre=f"Nombre{indice + 1}",
                apellido=f"Apellido{indice + 1}",
                bloque="Bloque",
                presente=indice < presentes,
                banca=indice + 1,
                dispositivo_votacion=f"dev{indice + 1}",
            )
            for indice in range(total)
        ]

    return construir


@pytest.fixture(autouse=True)
def aislar_estado_global(monkeypatch, tmp_path, concejales):
    sesion_service = sesion_service_module.sesion_service
    votacion_service = votacion_service_module.votacion_service

    sesion_service.sesion_actual = None
    votacion_service.votacion_actual = None
    info_pantallas_service.info_pantallas_actual = None
    Votacion._next_id = 1
    Voto._next_id = 1
    logging._log_seq = 0
    logging._log_ram_tail.clear()

    monkeypatch.setattr(settings, "quorum", 2)
    monkeypatch.setattr(settings, "log_dir", str(tmp_path / "logs"))
    monkeypatch.setattr(
        sesion_service_module,
        "cargar_concejales_desde_archivo",
        lambda _ruta: concejales(),
    )

    yield

    sesion_service.sesion_actual = None
    votacion_service.votacion_actual = None
    info_pantallas_service.info_pantallas_actual = None
    logging._log_seq = 0
    logging._log_ram_tail.clear()
