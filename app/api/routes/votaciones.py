from fastapi import APIRouter, HTTPException, Body

from app.services.votacion_service import votacion_service
from app.models.votacion import Votacion

router = APIRouter(
    prefix="/votaciones",
    tags=["votaciones"],
)


@router.post("/abrir")
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


@router.post("/cerrar-forzado")
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


@router.get("/actual")
def obtener_votacion_actual():
    """
    Devuelve la votación actual, si existe.
    """
    votacion = votacion_service.obtener_votacion_actual()
    if votacion is None:
        return {
            "hay_votacion": False,
            "votacion": None,
        }

    return {
        "hay_votacion": True,
        "votacion": votacion.to_dict(),
    }
