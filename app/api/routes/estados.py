from fastapi import APIRouter

from app.services.sesion_service import sesion_service
from app.utils.logging import get_log_tail


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
            "eventos":get_log_tail(),
        }

    return {
        "hay_sesion": True,
        "sesion": sesion.to_dict(),
        "eventos":get_log_tail(),
    }
