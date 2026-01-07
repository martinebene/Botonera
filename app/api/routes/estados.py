from fastapi import APIRouter, HTTPException, Body

from app.services.sesion_service import sesion_service
from app.models.sesion import Sesion

router = APIRouter(
    prefix="/estados",
    tags=["estados"],
)



@router.get("/estado_global")
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
