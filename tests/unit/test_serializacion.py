from datetime import datetime

from app.models.InfoPantallas import InfoPantallas
from app.models.sesion import Sesion
from app.models.votacion import Votacion
from app.models.voto import ValorVoto, Voto
from app.services import sesion_service as sesion_service_module


def test_concejal_voto_y_votacion_serializan_enums_y_fechas(concejales):
    concejal = concejales(total=1)[0]
    voto = Voto(concejal, ValorVoto.ABSTENCION, datetime(2026, 1, 2, 3, 4, 5), id=7)
    votacion = Votacion(sesion_service_module.sesion_service, 4, "Tipo", "Tema", True, 0, id=8)
    votacion.hora_inicio = datetime(2026, 1, 2, 3, 4, 5)
    votacion.votos.append(voto)

    assert concejal.to_dict()["mostrar_test"] is False
    assert voto.to_dict()["valor_voto"] == "Abstención"
    assert voto.to_dict()["hora_emision"] == "2026-01-02T03:04:05"
    assert votacion.to_dict()["estado"] == "EN_CURSO"
    assert votacion.to_dict()["hora_fin"] is None
    assert votacion.to_dict()["votos"][0]["id"] == 7


def test_sesion_to_dict_conserva_objeto_en_uso_de_palabra_y_serializa_cola(concejales):
    sesion = Sesion()
    concejal = concejales(total=1)[0]
    sesion.concejales = [concejal]
    sesion.pedidos_uso_de_palabra.append(concejal)
    sesion.en_uso_de_palabra = concejal

    serializada = sesion.to_dict()

    assert serializada["hora_inicio"] is None
    assert serializada["pedidos_uso_de_palabra"] == [concejal.to_dict()]
    assert serializada["en_uso_de_palabra"] is concejal


def test_info_pantallas_proyecta_sesion_y_bancas(concejales):
    sesion = Sesion()
    sesion.quorum = 2
    sesion.concejales = concejales()
    sesion.pedidos_uso_de_palabra.append(sesion.concejales[0])
    info = InfoPantallas()
    info.add_sesion(sesion)
    info.refrescar()

    serializada = info.to_dict()

    assert serializada["cantidad_presentes"] == 3
    assert serializada["diferencia_contra_quorum"] == 1
    assert serializada["pedidos_uso_de_palabra"] == ["Nombre1 Apellido1"]
    assert serializada["bancas"][0]["voto"] is None
