from fastapi import APIRouter, HTTPException, Body

from app.services.sesion_service import sesion_service
from app.models.sesion import Sesion

from app.services.votacion_service import votacion_service
from app.models.votacion import Votacion


router = APIRouter(
    prefix="/moderacion",
    tags=["moderacion"],
)


@router.post("/abrir_sesion")
def abrir_sesion(
    numero_sesion: int = Body(..., embed=True),
):
    """
    Endpoint para ABRIR una sesión.

    Body esperado:
        { "numero_sesion": 52 }
    """

    try:
        sesion: Sesion = sesion_service.abrir_sesion(numero_sesion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sesion.to_dict()


@router.post("/cerrar_sesion")
def cerrar_sesion():
    """
    Endpoint para CERRAR la sesión actual.
    """

    try:
        sesion: Sesion = sesion_service.cerrar_sesion()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sesion.to_dict()


@router.post("/abrir_votacion")
def abrir_votacion(
    numero: int = Body(..., embed=True),
    tipo: str = Body(...),
    tema: str = Body(...),
):
    """
    Abre una nueva votación en la sesión actual.

    Body esperado:
    {
      "numero": 1,
      "tipo": "ordinaria",
      "tema": "Aprobación del presupuesto"
    }
    """
    try:
        votacion: Votacion = votacion_service.abrir_votacion(numero=numero, tipo=tipo, tema=tema)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return votacion.to_dict()


@router.post("/cerrar_votacion")
def cerrar_votacion_forzado():
    """
    Fuerza el cierre de la votación actual.

    Si hay concejales presentes que no votaron, quedan registrados
    en el log del sistema.
    """
    try:
        votacion = votacion_service.cierre_forzado()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "votacion": votacion.to_dict(),
        "cerrada_forzada": True,
    }