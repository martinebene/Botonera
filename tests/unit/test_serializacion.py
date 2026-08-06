from datetime import datetime

from app.models.InfoPantallas import InfoPantallas
from app.models.sesion import Sesion
from app.models.votacion import Votacion
from app.models.voto import ValorVoto, Voto
from app.services import sesion_service as sesion_service_module


def test_concejal_voto_y_votacion_serializan_todos_los_campos(concejales):
    concejal = concejales(total=1)[0]
    voto = Voto(concejal, ValorVoto.ABSTENCION, datetime(2026, 1, 2, 3, 4, 5), id=7)
    votacion = Votacion(sesion_service_module.sesion_service, 4, "Tipo", "Tema", True, 0, id=8)
    votacion.hora_inicio = datetime(2026, 1, 2, 3, 4, 5)
    votacion.hora_fin = datetime(2026, 1, 2, 4, 5, 6)
    votacion.votos.append(voto)

    concejal_serializado = {
        "dni": "1",
        "nombre": "Nombre1",
        "apellido": "Apellido1",
        "bloque": "Bloque",
        "presente": True,
        "banca": 1,
        "dispositivo_votacion": "dev1",
        "mostrar_test": False,
    }
    assert concejal.to_dict() == concejal_serializado
    assert voto.to_dict() == {
        "id": 7,
        "concejal": concejal_serializado,
        "valor_voto": "Abstención",
        "hora_emision": "2026-01-02T03:04:05",
    }
    assert votacion.to_dict() == {
        "id": 8,
        "numero": 4,
        "tipo": "Tipo",
        "tema": "Tema",
        "estado": "EN_CURSO",
        "computa_sobre_los_presentes": True,
        "factor_mayoria_especial": 0,
        "hora_inicio": "2026-01-02T03:04:05",
        "hora_fin": "2026-01-02T04:05:06",
        "votos": [voto.to_dict()],
    }


def test_sesion_to_dict_serializa_listas_y_conserva_objeto_en_uso_de_palabra(concejales):
    sesion = Sesion()
    concejal = concejales(total=1)[0]
    voto = Voto(concejal, ValorVoto.POSITIVO, datetime(2026, 1, 2, 3, 4, 5), id=3)
    votacion = Votacion(sesion_service_module.sesion_service, 1, "Tipo", "Tema", False, 0.5, id=2)
    votacion.hora_inicio = datetime(2026, 1, 2, 3, 4, 5)
    votacion.votos.append(voto)
    sesion.transmision_en_vivo = True
    sesion.numero_sesion = 9
    sesion.abierta = True
    sesion.hora_apertura_recinto = datetime(2026, 1, 2, 1, 0, 0)
    sesion.hora_inicio = datetime(2026, 1, 2, 2, 0, 0)
    sesion.quorum = 1
    sesion.disposicion_bancas = '{"filas": []}'
    sesion.concejales = [concejal]
    sesion.votaciones = [votacion]
    sesion.pedidos_uso_de_palabra.append(concejal)
    sesion.en_uso_de_palabra = concejal

    serializada = sesion.to_dict()

    assert serializada == {
        "transmision_en_vivo": True,
        "numero_sesion": 9,
        "abierta": True,
        "hora_apertura_recinto": "2026-01-02T01:00:00",
        "hora_inicio": "2026-01-02T02:00:00",
        "hora_fin": None,
        "cantidad_concejales": 1,
        "cantidad_presentes": 1,
        "quorum": 1,
        "disposicion_bancas": '{"filas": []}',
        "concejales": [concejal.to_dict()],
        "votaciones": [votacion.to_dict()],
        "pedidos_uso_de_palabra": [concejal.to_dict()],
        "en_uso_de_palabra": concejal,
    }


def test_info_pantallas_sin_sesion_expone_valores_ausentes_actuales():
    info = InfoPantallas()
    info.refrescar()

    serializada = info.to_dict()

    assert datetime.fromisoformat(serializada["hora_actual"])
    assert serializada["hora_apertura_recinto"] is None
    assert serializada["sesion_abierta"] is None
    assert serializada["transmision_en_vivo"] is False
    assert serializada["numero_sesion"] is None
    assert serializada["cantidad_presentes"] is None
    assert serializada["diferencia_contra_quorum"] is None
    assert serializada["pedidos_uso_de_palabra"] == []
    assert serializada["bancas"] == []
    assert serializada["nro_votacion_en_curso"] is None
    assert serializada["votos_emitidos_votacion_en_curso"] is None
    assert "eventos" not in serializada
    assert "computa_sobre_los_presentes" not in serializada


def test_info_pantallas_proyecta_sesion_transmision_votacion_y_votos(concejales):
    sesion = Sesion()
    sesion.abierta = True
    sesion.numero_sesion = 3
    sesion.quorum = 2
    sesion.transmision_en_vivo = True
    sesion.hora_apertura_recinto = datetime(2026, 1, 2, 1, 0, 0)
    sesion.hora_inicio = datetime(2026, 1, 2, 2, 0, 0)
    sesion.concejales = concejales()
    sesion.pedidos_uso_de_palabra.append(sesion.concejales[1])
    sesion.en_uso_de_palabra = sesion.concejales[0]
    votacion = Votacion(sesion_service_module.sesion_service, 4, "Tipo", "Tema", True, 0)
    votacion.hora_inicio = datetime(2026, 1, 2, 3, 0, 0)
    votacion.votos.append(Voto(sesion.concejales[0], ValorVoto.POSITIVO, id=1))
    info = InfoPantallas()
    info.add_sesion(sesion)
    info.add_votacion(votacion)
    info.refrescar()

    serializada = info.to_dict()

    assert datetime.fromisoformat(serializada["hora_actual"])
    assert serializada["hora_apertura_recinto"] == "2026-01-02T01:00:00"
    assert serializada["sesion_abierta"] is True
    assert serializada["transmision_en_vivo"] is True
    assert serializada["numero_sesion"] == 3
    assert serializada["hora_inicio_sesion"] == "2026-01-02T02:00:00"
    assert serializada["hora_fin_sesion"] is None
    assert serializada["cantidad_presentes"] == 3
    assert serializada["diferencia_contra_quorum"] == 1
    assert serializada["pedidos_uso_de_palabra"] == ["Nombre2 Apellido2"]
    assert serializada["nro_votacion_en_curso"] == 4
    assert serializada["hora_apertura_votacion"] == "2026-01-02T03:00:00"
    assert serializada["tema_votacion_en_curso"] == "Tema"
    assert serializada["tipo_votacion_en_curso"] == "Tipo"
    assert serializada["votos_emitidos_votacion_en_curso"] == 1
    assert serializada["estado_votacion"] == "Votacion Nº4 en curso: 1 votos emitidos."
    assert serializada["titulo_votacion"] == "Nº4 de tipo Tipo sin mayoria especial, sobre presentes"
    assert serializada["bancas"][0] == {
        "numero_banca": 1,
        "nombre_concejal": "Nombre1 Apellido1",
        "en_uso_palabra": True,
        "presente": True,
        "test": False,
        "voto": "POSITIVO",
    }
    assert serializada["bancas"][1]["en_uso_palabra"] is False
    assert serializada["bancas"][1]["voto"] is None
