from fastapi import APIRouter, HTTPException, Body

from app.services import sesion_service
from app.models.sesion import Sesion

router = APIRouter()


@router.post("/abrir")
def abrir_sesion(
    numero_sesion: int = Body(..., embed=True),
):
    """
    Endpoint para ABRIR una sesión.

    Body esperado:
        { "numero_sesion": 5 }

    Reglas:
    - Si ya hay una sesión abierta -> HTTP 400
    - Si no hay, abre una nueva y la devuelve.
    """
    try:
        sesion: Sesion = sesion_service.abrir_sesion(numero_sesion)
    except KeyError as e:
        code = e.args[0] if e.args else None
        if code == "ya_hay_abierta":
            raise HTTPException(
                status_code=400,
                detail="Ya hay una sesión abierta. Debe cerrarla antes de abrir otra.",
            )
        # Cualquier otra cosa inesperada
        raise

    return sesion.to_dict()


@router.post("/cerrar")
def cerrar_sesion():
    """
    Endpoint para CERRAR la sesión actual.

    Reglas:
    - Si no hay sesión -> HTTP 400 ("No hay ninguna sesión abierta.")
    - Si se cierra correctamente:
        * se escribe en sesiones_log.txt
        * se devuelve la sesión (con hora_fin)
    """
    try:
        sesion: Sesion = sesion_service.cerrar_sesion()
    except KeyError as e:
        code = e.args[0] if e.args else None

        if code == "no_hay_sesion":
            raise HTTPException(
                status_code=400,
                detail="No hay ninguna sesión abierta.",
            )

        if code == "ya_cerrada":
            # Por diseño casi no deberíamos llegar acá, pero lo contemplamos
            raise HTTPException(
                status_code=400,
                detail="La sesión ya está cerrada.",
            )

        raise

    return sesion.to_dict()


@router.get("/")
def estado_sesion():
    """
    Devuelve el estado de la sesión actual.

    - hay_sesion: bool
    - sesion: datos de la sesión o None
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
