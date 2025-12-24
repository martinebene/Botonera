# ===============================
# Script: crear_estructura_simple.ps1
# Crea una API FastAPI simple, sin DB, con sesiones en memoria
# ===============================

Write-Host "Creando estructura simple de la API del Concejo..." -ForegroundColor Cyan

function Ensure-Dir {
    param([string]$path)
    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "Directorio creado: $path"
    } else {
        Write-Host "Directorio ya existía: $path"
    }
}

function Write-File {
    param(
        [string]$path,
        [string]$content
    )
    Set-Content -Path $path -Value $content -Force
    Write-Host "Archivo generado: $path"
}

# -------------------------------
# Directorios
# -------------------------------

Ensure-Dir "app"
Ensure-Dir "app\models"
Ensure-Dir "app\services"
Ensure-Dir "app\api"
Ensure-Dir "app\api\routes"

# -------------------------------
# app/__init__.py
# -------------------------------
Write-File "app\__init__.py" ""

# -------------------------------
# app/models/__init__.py
# -------------------------------
Write-File "app\models\__init__.py" ""

# -------------------------------
# app/services/__init__.py
# -------------------------------
Write-File "app\services\__init__.py" ""

# -------------------------------
# app/api/__init__.py
# -------------------------------
Write-File "app\api\__init__.py" ""

# -------------------------------
# app/api/routes/__init__.py
# -------------------------------
Write-File "app\api\routes\__init__.py" @"
from . import sesiones

__all__ = ["sesiones"]
"@

# -------------------------------
# app/models/sesion.py
# -------------------------------
Write-File "app\models\sesion.py" @"
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Sesion:
    \"""
    Clase de dominio pura, sin base de datos.

    Sesion:
    + id: Integer
    + numeroSesion: Integer
    + abierta: Boolean
    + horaInicio: TimeStamp
    + horaFin: TimeStamp
    + listaDeVotaciones[ ]: List Votacion   (todavía no implementadas)
    + listaDeDebates[ ]: List Debate
    + listaDeConcejales[ ]: List Concejal
    \"""

    id: int
    numero_sesion: int
    abierta: bool = True
    hora_inicio: datetime = field(default_factory=datetime.now)
    hora_fin: Optional[datetime] = None

    votaciones: List[dict] = field(default_factory=list)
    debates: List[dict] = field(default_factory=list)
    concejales: List[dict] = field(default_factory=list)

    def cerrar(self) -> None:
        \"""Marca la sesión como cerrada y registra la hora de fin.\\"""
        self.abierta = False
        self.hora_fin = datetime.now()

    def to_dict(self) -> dict:
        \"""Convierte la sesión a un diccionario simple (para JSON).\\"""
        return {
            "id": self.id,
            "numero_sesion": self.numero_sesion,
            "abierta": self.abierta,
            "hora_inicio": self.hora_inicio.isoformat() if self.hora_inicio else None,
            "hora_fin": self.hora_fin.isoformat() if self.hora_fin else None,
            "votaciones": self.votaciones,
            "debates": self.debates,
            "concejales": self.concejales,
        }
"@

# -------------------------------
# app/services/sesion_service.py
# -------------------------------
Write-File "app\services\sesion_service.py" @"
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
    \"""
    Crea una nueva Sesion en memoria.

    - Usa NEXT_ID como id autoincremental.
    - Marca abierta=True y hora_inicio=ahora.
    - NO escribe en el log todavía (solo al cerrar).
    \"""
    global NEXT_ID

    sesion = Sesion(id=NEXT_ID, numero_sesion=numero_sesion)
    SESIONES.append(sesion)
    NEXT_ID += 1
    return sesion


def _buscar_sesion_por_id(sesion_id: int) -> Optional[Sesion]:
    \"""Busca una sesión por id en la lista SESIONES.\\"""
    for s in SESIONES:
        if s.id == sesion_id:
            return s
    return None


def cerrar_sesion(sesion_id: int) -> Sesion:
    \"""
    Cierra una sesión existente.

    - Si no existe -> KeyError("no_encontrada")
    - Si ya estaba cerrada -> KeyError("ya_cerrada")
    - Si todo OK:
        * marca hora_fin
        * escribe una línea en el log:
          "se abrio sesion nro X, a la hora Y, y se cerro a la hora Z"
    \"""
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
    \"""Devuelve todas las sesiones en memoria.\\"""
    return SESIONES
"@

# -------------------------------
# app/api/routes/sesiones.py
# -------------------------------
Write-File "app\api\routes\sesiones.py" @"
from fastapi import APIRouter, HTTPException, Body
from typing import List

from app.services import sesion_service
from app.models.sesion import Sesion

router = APIRouter()


@router.post("/abrir")
def abrir_sesion(
    numero_sesion: int = Body(..., embed=True),
):
    \"""
    Endpoint para abrir una sesión.

    Body esperado:
        { "numero_sesion": 5 }

    Llama a sesion_service.abrir_sesion y devuelve la sesión creada.
    \"""
    sesion: Sesion = sesion_service.abrir_sesion(numero_sesion)
    return sesion.to_dict()


@router.post("/{sesion_id}/cerrar")
def cerrar_sesion(sesion_id: int):
    \"""
    Endpoint para cerrar una sesión.

    - Si la sesión no existe -> HTTP 404
    - Si ya estaba cerrada -> HTTP 400
    - Si se cierra correctamente:
        * se registra una línea en sesiones_log.txt
        * se devuelve la sesión cerrada
    \"""
    try:
        sesion: Sesion = sesion_service.cerrar_sesion(sesion_id)
    except KeyError as e:
        if str(e) == "no_encontrada":
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        if str(e) == "ya_cerrada":
            raise HTTPException(status_code=400, detail="La sesión ya está cerrada")
        raise

    return sesion.to_dict()


@router.get("/")
def listar_sesiones():
    \"""Devuelve todas las sesiones en memoria.\\"""
    sesiones = sesion_service.listar_sesiones()
    return [s.to_dict() for s in sesiones]
"@

# -------------------------------
# app/main.py
# -------------------------------
Write-File "app\main.py" @"
from fastapi import FastAPI

from app.api.routes import sesiones

app = FastAPI(
    title="API Concejo Deliberante (memoria, sin DB)",
    version="0.1.0",
)


@app.get("/")
def root():
    \"""
    Endpoint simple de prueba.
    \"""
    return {"mensaje": "API Concejo funcionando (memoria, sin DB)"}


# Registramos el router de sesiones
app.include_router(sesiones.router, prefix="/sesiones", tags=["Sesiones"])
"@

Write-Host "Estructura simple generada correctamente." -ForegroundColor Green
