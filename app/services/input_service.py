from typing import Dict, Any

from app.services.sesion_service import sesion_service


def procesar_pulsacion(dispositivo: str, tecla: str) -> Dict[str, Any]:
    """
    Procesa una pulsación de tecla proveniente de un dispositivo físico.

    - Verifica que haya una sesión abierta.
    - Busca el concejal asignado a ese dispositivo.
    - Por ahora SOLO valida y devuelve la información.
      (Más adelante enganchamos votos y debates.)

    Devuelve un diccionario con:
    - aceptada: bool
    - motivo: str (si no fue aceptada)
    - dispositivo, tecla
    - concejal: dict (si se encontró)
    """

    sesion = sesion_service.obtener_sesion_actual()

    if sesion is None or not sesion.abierta:
        return {
            "aceptada": False,
            "motivo": "no_hay_sesion_abierta",
            "dispositivo": dispositivo,
            "tecla": tecla,
        }

    concejal = None
    for c in sesion.concejales:
        if c.dispositivo_votacion == dispositivo:
            concejal = c
            break

    if concejal is None:
        return {
            "aceptada": False,
            "motivo": "dispositivo_no_asignado",
            "dispositivo": dispositivo,
            "tecla": tecla,
        }

    return {
        "aceptada": True,
        "motivo": "",
        "dispositivo": dispositivo,
        "tecla": tecla,
        "concejal": concejal.to_dict(),
    }
