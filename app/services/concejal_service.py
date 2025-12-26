import csv
from typing import List

from app.models.concejal import Concejal


def cargar_concejales_desde_archivo(ruta: str) -> List[Concejal]:
    """
    Lee el archivo CSV de concejales y devuelve una lista de objetos Concejal.

    Se espera un CSV con encabezados:
    dni,nombre,apellido,bloque,presente,banca,dispositivo_votacion
    """
    concejales: List[Concejal] = []

    with open(ruta, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            presente_str = (row.get("presente") or "").strip().lower()
            presente = presente_str in ("true", "1", "si", "sí", "y", "yes")

            banca = int(row["banca"]) if row.get("banca") not in (None, "") else 0

            concejal = Concejal(
                dni=row["dni"],
                nombre=row["nombre"],
                apellido=row["apellido"],
                bloque=row.get("bloque", ""),
                presente=presente,
                banca=banca,
                dispositivo_votacion=row.get("dispositivo_votacion") or None,
            )
            concejales.append(concejal)

    return concejales
