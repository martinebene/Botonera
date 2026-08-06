import pytest

from app.services import sesion_service as sesion_service_module
from app.services.input_service import procesar_pulsacion
from app.services.votacion_service import votacion_service


def preparar_abierta():
    servicio = sesion_service_module.sesion_service
    sesion = servicio.preparar_sesion()
    servicio.abrir_sesion(1)
    return sesion


def test_pulsacion_sin_recinto_preparado_y_dispositivo_no_asignado():
    assert procesar_pulsacion("dev1", "9") == {
        "aceptada": False,
        "motivo": "no_hay_sesion_abierta",
        "dispositivo": "dev1",
        "tecla": "9",
    }

    preparar_abierta()
    respuesta = procesar_pulsacion("desconocido", "9")
    assert respuesta == {
        "aceptada": False,
        "motivo": "dispositivo_no_asignado",
        "dispositivo": "desconocido",
        "tecla": "9",
    }


def test_teclas_de_presencia_test_y_palabra():
    sesion = preparar_abierta()
    concejal = sesion.concejales[0]
    concejal.presente = False

    presencia = procesar_pulsacion("dev1", "9")
    visual = procesar_pulsacion("dev1", "8")
    pedido = procesar_pulsacion("dev1", "7")
    retiro = procesar_pulsacion("dev1", "7")

    assert presencia["motivo"] == "cambio_presencia"
    assert visual["motivo"] == "mostrar_test"
    assert visual["concejal"]["mostrar_test"] is True
    assert pedido["motivo"] == retiro["motivo"] == "tecla_uso_palabra"
    assert list(sesion.pedidos_uso_de_palabra) == []


def test_tecla_palabra_finaliza_turno_y_ausente_es_rechazado():
    sesion = preparar_abierta()
    concejal = sesion.concejales[0]
    sesion_service_module.sesion_service.encolar_uso_palabra(concejal)
    sesion_service_module.sesion_service.otorgar_uso_palabra()

    assert procesar_pulsacion("dev1", "7")["motivo"] == "fin_uso_palabra"
    concejal.presente = False
    assert procesar_pulsacion("dev1", "7")["motivo"] == "concejal_ausente"


@pytest.mark.parametrize(("tecla", "valor"), [("1", "Positivo"), ("2", "Abstención"), ("3", "Negativo")])
def test_teclas_de_voto_registran_el_valor_vigente(tecla, valor):
    sesion = preparar_abierta()
    votacion_service.abrir_votacion(1, "Ordinaria", "Tema", True, 0)

    respuesta = procesar_pulsacion("dev1", tecla)

    assert respuesta["aceptada"] is True
    assert respuesta["motivo"] == "voto_registrado"
    assert respuesta["valor_voto"] == valor


def test_voto_ausente_sin_votacion_doble_voto_y_tecla_no_soportada():
    sesion = preparar_abierta()
    sesion.concejales[0].presente = False
    votacion_service.abrir_votacion(1, "Ordinaria", "Tema", True, 0)
    assert procesar_pulsacion("dev1", "1")["motivo"] == "concejal_ausente"

    sesion.concejales[0].presente = True
    assert procesar_pulsacion("dev1", "1")["aceptada"] is True
    assert procesar_pulsacion("dev1", "1")["motivo"] == "concejal_ya_voto"
    assert procesar_pulsacion("dev1", "4")["motivo"] == "tecla_no_soportada"


def test_voto_sin_votacion_abierta_incluye_concejal_en_respuesta():
    preparar_abierta()
    respuesta = procesar_pulsacion("dev1", "1")

    assert respuesta["aceptada"] is False
    assert respuesta["motivo"] == "no_hay_votacion_abierta"
    assert respuesta["concejal"]["dispositivo_votacion"] == "dev1"
