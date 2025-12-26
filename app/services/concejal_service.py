import csv
from typing import List

from app.models.concejal import Concejal


def cargar_concejales_desde_archivo(ruta: str) -> List[Concejal]:
    """
    Carga concejales desde un archivo CSV.

    Formato esperado:
    dni,nombre,apellido,bloque,presente,banca,dispositivo_votacion
    """

    concejales: List[Concejal] = []

    with open(ruta, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            if not fila.get("dni"):
                continue

            presente_str = (fila.get("presente") or "").strip().lower()
            presente = presente_str in ("true", "1", "si", "sí", "yes")

            banca_str = (fila.get("banca") or "0").strip()
            try:
                banca = int(banca_str)
            except ValueError:
                banca = 0

            concejal = Concejal(
                dni=fila.get("dni", "").strip(),
                nombre=fila.get("nombre", "").strip(),
                apellido=fila.get("apellido", "").strip(),
                bloque=fila.get("bloque", "").strip(),
                presente=presente,
                banca=banca,
                dispositivo_votacion=(fila.get("dispositivo_votacion") or "").strip(),
            )
            concejales.append(concejal)

    return concejales
