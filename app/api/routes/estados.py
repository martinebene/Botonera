from fastapi import APIRouter

from app.config import settings
from app.services.sesion_service import sesion_service
from app.services.InfoPantallasService import info_pantallas_service
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

@router.get("/info_pantallas")
def info_pantallas():
    """
    Devuelve el estado para las pantallas de la recinto/sesión actual.
    """
    info_pantallas = info_pantallas_service.obtener_info_pantallas()

    return info_pantallas.to_dict()

@router.get("/configuracion")
def info_config_pantallas():
    """
    Devuelve la configuracion para frontends.
    """
    if settings is None:
        return {
            "settings": None,
        }

    return settings.to_dict