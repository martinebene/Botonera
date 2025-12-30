from fastapi import APIRouter, Body

from app.services.input_service import procesar_pulsacion

router = APIRouter(
    prefix="/entradas",
    tags=["entradas"],
)


@router.post("/tecla")
def recibir_tecla(
    dispositivo: str = Body(..., embed=True),
    tecla: str = Body(..., embed=True),
):
    """
    Recibe una pulsación desde un dispositivo físico (teclado).

    Body esperado:
    {
      "dispositivo": "ruta_o_id_del_dispositivo",
      "tecla": "1"
    }
    """
    return procesar_pulsacion(dispositivo, tecla)
