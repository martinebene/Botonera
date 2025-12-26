from fastapi import APIRouter, HTTPException, Body

from app.services.input_service import procesar_pulsacion

router = APIRouter(
    prefix="/entradas",
    tags=["entradas"],
)


@router.post("/tecla")
def recibir_pulsacion(payload: dict = Body(...)):
    """
    Endpoint para recibir pulsaciones de teclas desde el cliente de botonera.

    Espera un JSON:
    {
      "dispositivo": "ruta_del_dispositivo_en_linux",
      "tecla": "1"
    }
    """

    dispositivo = payload.get("dispositivo")
    tecla = payload.get("tecla")

    if not dispositivo or tecla is None:
        raise HTTPException(
            status_code=400,
            detail="Se requieren los campos 'dispositivo' y 'tecla'.",
        )

    resultado = procesar_pulsacion(dispositivo=dispositivo, tecla=str(tecla))

    if not resultado.get("aceptada", False):
        raise HTTPException(
            status_code=400,
            detail=resultado.get("motivo", "pulsacion_rechazada"),
        )

    return resultado
