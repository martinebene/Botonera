from fastapi import APIRouter, HTTPException, Body

from app.services.sesion_service import sesion_service
from app.models.sesion import Sesion

router = APIRouter(
    prefix="/sesiones",
    tags=["sesiones"],
)


@router.post("/abrir")
def abrir_sesion(
    numero_sesion: int = Body(..., embed=True),
):
    """
    Endpoint para ABRIR una sesión.

    Body esperado:
        { "numero_sesion": 5 }
    """

    try:
        sesion: Sesion = sesion_service.abrir_sesion(numero_sesion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sesion.to_dict()


@router.post("/cerrar")
def cerrar_sesion():
    """
    Endpoint para CERRAR la sesión actual.
    """

    try:
        sesion: Sesion = sesion_service.cerrar_sesion()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sesion.to_dict()


@router.get("/")
def estado_sesion():
    """
    Devuelve el estado de la sesión actual.
    """

    sesion = sesion_service.obtener_sesion_actual()

    if sesion is None:
        return {
            "hay_sesion": False,
            "sesion": None,
        }

    return {
        "hay_sesion": True,
        "sesion": sesion.to_dict(),
    }
