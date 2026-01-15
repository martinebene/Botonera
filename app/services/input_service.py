from typing import Dict, Any
from datetime import datetime

from app.services.sesion_service import sesion_service
from app.services.votacion_service import votacion_service
from app.models.votacion import EstadosVotacion
from app.models.voto import Voto, ValorVoto
from app.config import settings


def _log_pulsacion_raw(dispositivo: str, tecla: str) -> None:
    """
    Log básico, se escribe APENAS llega la pulsación,
    antes de cualquier validación de sesión o concejal.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = (
        f"[{timestamp}] PULSACION_RAW; "
        f"dispositivo={dispositivo}; "
        f"tecla={tecla}"
    )
    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _log_pulsacion_procesada(
    aceptada: bool,
    motivo: str,
    dispositivo: str,
    tecla: str,
    concejal_info: str,
) -> None:
    """
    Log detallado de la pulsación luego de procesar la lógica.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_str = "aceptada" if aceptada else "rechazada"

    linea = (
        f"[{timestamp}] PULSACION {estado_str}; "
        f"dispositivo={dispositivo}; "
        f"tecla={tecla}; "
        f"concejal={concejal_info}; "
        f"motivo={motivo}"
    )

    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def procesar_pulsacion(dispositivo: str, tecla: str) -> Dict[str, Any]:
    """
    Procesa una pulsación de tecla proveniente de un dispositivo físico.

    Reglas:
    - Siempre loguea PULSACION_RAW.
    - Si no hay sesión abierta -> rechaza.
    - Si el dispositivo no está asignado a un concejal -> rechaza.
    - Tecla 7:
        * alterna el estado presente/ausente del concejal.
        * si hay votación abierta, se recalcula si corresponde cierre automático.
    - Teclas 1/2/3 durante votación:
        * 1 -> SI
        * 2 -> ABSTENCION
        * 3 -> NO
        * requiere votación abierta y concejal presente.
        * crea un Voto y lo registra en la votación.
    - Cualquier otra tecla -> rechaza (por ahora).
    """

    # 1) Log crudo inmediato
    _log_pulsacion_raw(dispositivo=dispositivo, tecla=tecla)

    # 2) Verificar sesión
    sesion = sesion_service.obtener_sesion_actual()

    if sesion is None or not sesion.abierta:
        motivo = "no_hay_sesion_abierta"
        _log_pulsacion_procesada(
            aceptada=False,
            motivo=motivo,
            dispositivo=dispositivo,
            tecla=tecla,
            concejal_info="N/A",
        )
        return {
            "aceptada": False,
            "motivo": motivo,
            "dispositivo": dispositivo,
            "tecla": tecla,
        }

    # 3) Buscar concejal por dispositivo
    concejal = None
    for c in sesion.concejales:
        if c.dispositivo_votacion == dispositivo:
            concejal = c
            break

    if concejal is None:
        motivo = "dispositivo_no_asignado"
        _log_pulsacion_procesada(
            aceptada=False,
            motivo=motivo,
            dispositivo=dispositivo,
            tecla=tecla,
            concejal_info="N/A",
        )
        return {
            "aceptada": False,
            "motivo": motivo,
            "dispositivo": dispositivo,
            "tecla": tecla,
        }

    concejal_info = f"{concejal.apellido}, {concejal.nombre} (dni={concejal.dni})"

    # 4) Tecla 7: toggle presente/ausente
    if tecla == "7":
        concejal.presente = not concejal.presente
        sesion.presentes = sesion_service.cantidad_concejales_presentes()

        motivo = "toggle_presente"

        # Log de la pulsación de toggle
        _log_pulsacion_procesada(
            aceptada=True,
            motivo=motivo,
            dispositivo=dispositivo,
            tecla=tecla,
            concejal_info=concejal_info,
        )

        votacion_service.recalcular_cierre_por_cambio_en_presencia()

        return 


    # 5) Tecla 9: pedido de palabra
    if tecla == "9":
        
        # Concejal debe estar presente
        if concejal.presente:
            sesion_service.encolar_uso_palabra(concejal) #encoola y desencola
            return
        else:
            motivo = "concejal_ausente"
            _log_pulsacion_procesada(
                aceptada=False,
                motivo=motivo,
                dispositivo=dispositivo,
                tecla=tecla,
                concejal_info=concejal_info,
            )
            return {
                "aceptada": False,
                "motivo": motivo,
                "dispositivo": dispositivo,
                "tecla": tecla,
                "concejal": concejal.to_dict(),
            }




    # 6) Teclas de votación: 1 (SI), 2 (ABSTENCION), 3 (NO)
    if tecla in ("1", "2", "3"):
        # Debe haber votación abierta
        votacion = votacion_service.obtener_votacion_actual()
        if votacion is None or (votacion.estado != EstadosVotacion.EN_CURSO):
            motivo = "no_hay_votacion_abierta"
            _log_pulsacion_procesada(
                aceptada=False,
                motivo=motivo,
                dispositivo=dispositivo,
                tecla=tecla,
                concejal_info=concejal_info,
            )
            return {
                "aceptada": False,
                "motivo": motivo,
                "dispositivo": dispositivo,
                "tecla": tecla,
                "concejal": concejal.to_dict(),
            }

        # Concejal debe estar presente
        if not concejal.presente:
            motivo = "concejal_ausente"
            _log_pulsacion_procesada(
                aceptada=False,
                motivo=motivo,
                dispositivo=dispositivo,
                tecla=tecla,
                concejal_info=concejal_info,
            )
            return {
                "aceptada": False,
                "motivo": motivo,
                "dispositivo": dispositivo,
                "tecla": tecla,
                "concejal": concejal.to_dict(),
            }

        mapa_voto = {
            "1": ValorVoto.POSITIVO,
            "2": ValorVoto.ABSTENCION,
            "3": ValorVoto.NEGATIVO,
        }
        valor_voto = mapa_voto[tecla]

        voto = Voto(concejal=concejal, valor_voto=valor_voto)

        try:
            votacion_service.registrar_voto(voto)
        except ValueError as e:
            motivo = str(e)
            _log_pulsacion_procesada(
                aceptada=False,
                motivo=motivo,
                dispositivo=dispositivo,
                tecla=tecla,
                concejal_info=concejal_info,
            )
            return {
                "aceptada": False,
                "motivo": motivo,
                "dispositivo": dispositivo,
                "tecla": tecla,
                "concejal": concejal.to_dict(),
            }

        # Si llegó hasta acá, el voto se registró correctamente
        motivo = "voto_registrado"
        _log_pulsacion_procesada(
            aceptada=True,
            motivo=motivo,
            dispositivo=dispositivo,
            tecla=tecla,
            concejal_info=concejal_info,
        )

        return {
            "aceptada": True,
            "motivo": "",
            "accion": "voto_registrado",
            "dispositivo": dispositivo,
            "tecla": tecla,
            "concejal": concejal.to_dict(),
            "valor_voto": valor_voto,
        }

    # 6) Cualquier otra tecla: de momento la ignoramos a nivel de negocio
    motivo = "tecla_no_soportada"
    _log_pulsacion_procesada(
        aceptada=False,
        motivo=motivo,
        dispositivo=dispositivo,
        tecla=tecla,
        concejal_info=concejal_info,
    )
    return {
        "aceptada": False,
        "motivo": motivo,
        "dispositivo": dispositivo,
        "tecla": tecla,
        "concejal": concejal.to_dict(),
    }
