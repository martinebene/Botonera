from fastapi import APIRouter, HTTPException, Body
from typing import List

from app.services import sesion_service
from app.models.sesion import Sesion

router = APIRouter()


@router.post("/abrir")
def abrir_sesion(
    numero_sesion: int = Body(..., embed=True),
):
    """
    Endpoint para abrir una sesión.

    Body esperado:
        { "numero_sesion": 5 }

    Llama a sesion_service.abrir_sesion y devuelve la sesión creada.
    """
    sesion: Sesion = sesion_service.abrir_sesion(numero_sesion)
    return sesion.to_dict()


@router.post("/{sesion_id}/cerrar")
def cerrar_sesion(sesion_id: int):
    """
    Endpoint para cerrar una sesión.

    - Si la sesión no existe -> HTTP 404
    - Si ya estaba cerrada -> HTTP 400
    - Si se cierra correctamente:
        * se registra una línea en sesiones_log.txt
        * se devuelve la sesión cerrada
    """
    try:
        sesion: Sesion = sesion_service.cerrar_sesion(sesion_id)
    except KeyError as e:
        
         # e.args[0] contiene exactamente el "código" que le pasamos al KeyError
        code = e.args[0] if e.args else None

        if code == "no_encontrada":
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        if code == "ya_cerrada":
            raise HTTPException(status_code=400, detail="La sesión ya está cerrada")

        # Cualquier otro motivo lo dejamos explotar como 500 (error interno)
        raise

    return sesion.to_dict()


@router.get("/")
def listar_sesiones():
    """Devuelve todas las sesiones en memoria."""
    sesiones = sesion_service.listar_sesiones()
    return [s.to_dict() for s in sesiones]
