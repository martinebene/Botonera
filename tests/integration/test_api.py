from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.services import sesion_service as sesion_service_module
from app.services.InfoPantallasService import info_pantallas_service


VOTACION = {
    "numero": 1,
    "tipo": "Ordinaria",
    "tema": "Tema",
    "computa_sobre_los_presentes": True,
    "factor_mayoria_especial": 0,
}

INFO_PANTALLAS_CAMPOS = {
    "hora_actual",
    "hora_apertura_recinto",
    "sesion_abierta",
    "transmision_en_vivo",
    "numero_sesion",
    "hora_inicio_sesion",
    "hora_fin_sesion",
    "cantidad_presentes",
    "diferencia_contra_quorum",
    "pedidos_uso_de_palabra",
    "bancas",
    "nro_votacion_en_curso",
    "hora_apertura_votacion",
    "tema_votacion_en_curso",
    "tipo_votacion_en_curso",
    "votos_emitidos_votacion_en_curso",
    "estado_votacion",
    "titulo_votacion",
}


def refrescar_info_pantallas():
    if info_pantallas_service.info_pantallas_actual is not None:
        info_pantallas_service.info_pantallas_actual.ultimo_refresco = None


def preparar_y_abrir(client):
    assert client.post("/moderacion/preparar_sesion").json() == {"messege": "Ok preparar sesion"}
    assert client.post("/moderacion/abrir_sesion", json={"numero_sesion": 1}).json() == {
        "messege": "Ok abrir sesion"
    }


def test_aplicacion_estados_sin_sesion_y_configuracion():
    with TestClient(app) as client:
        assert client.get("/").json()["status"] == "ok"
        global_ = client.get("/estados/estado_global")
        pantallas = client.get("/estados/info_pantallas")
        configuracion = client.get("/estados/configuracion")

    assert global_.status_code == 200
    assert global_.json() == {"hay_sesion": False, "sesion": None, "eventos": global_.json()["eventos"]}
    assert isinstance(global_.json()["eventos"], list)
    assert pantallas.status_code == 200
    assert set(pantallas.json()) == INFO_PANTALLAS_CAMPOS
    assert pantallas.json()["sesion_abierta"] is None
    assert pantallas.json()["bancas"] == []
    assert pantallas.json()["nro_votacion_en_curso"] is None
    assert "eventos" not in pantallas.json()
    assert configuracion.status_code == 200
    assert configuracion.json()["quorum"] == 2
    assert configuracion.json()["concejales_file"] == "concejales-ficticios.csv"


def test_api_sesion_caracteriza_exitos_rechazos_y_estado_global():
    with TestClient(app) as client:
        sin_recinto = client.post("/moderacion/abrir_sesion", json={"numero_sesion": 1})
        sin_sesion = client.post("/moderacion/cerrar_sesion")

        preparada = client.post("/moderacion/preparar_sesion")
        repetida = client.post("/moderacion/preparar_sesion")
        estado_preparado = client.get("/estados/estado_global")
        abierta = client.post("/moderacion/abrir_sesion", json={"numero_sesion": 5})
        repetida_abierta = client.post("/moderacion/abrir_sesion", json={"numero_sesion": 6})
        estado_abierto = client.get("/estados/estado_global")
        cerrada = client.post("/moderacion/cerrar_sesion")
        cierre_repetido = client.post("/moderacion/cerrar_sesion")

    assert sin_recinto.status_code == 400
    assert sin_recinto.json() == {"detail": "no_hay_recinto_preparado"}
    assert sin_sesion.status_code == 400
    assert sin_sesion.json() == {"detail": "no_hay_sesión_abierta"}
    assert preparada.status_code == 200
    assert preparada.json() == {"messege": "Ok preparar sesion"}
    assert repetida.status_code == 400
    assert repetida.json() == {"detail": "ya_hay_sesión_preparada"}
    assert estado_preparado.json()["hay_sesion"] is True
    assert estado_preparado.json()["sesion"]["abierta"] is False
    assert estado_preparado.json()["sesion"]["numero_sesion"] is None
    assert estado_preparado.json()["sesion"]["hora_inicio"] is None
    assert estado_preparado.json()["sesion"]["cantidad_concejales"] == 3
    assert estado_preparado.json()["sesion"]["cantidad_presentes"] == 3
    assert estado_preparado.json()["sesion"]["quorum"] == 2
    assert estado_preparado.json()["sesion"]["votaciones"] == []
    assert estado_preparado.json()["sesion"]["pedidos_uso_de_palabra"] == []
    assert estado_preparado.json()["sesion"]["en_uso_de_palabra"] is None
    assert abierta.status_code == 200
    assert abierta.json() == {"messege": "Ok abrir sesion"}
    assert repetida_abierta.status_code == 400
    assert repetida_abierta.json() == {"detail": "ya_hay_sesión_abierta"}
    assert estado_abierto.json()["sesion"]["numero_sesion"] == 5
    assert estado_abierto.json()["sesion"]["abierta"] is True
    assert datetime.fromisoformat(estado_abierto.json()["sesion"]["hora_inicio"])
    assert cerrada.status_code == 200
    assert cerrada.json() == {"messege": "Ok cerrar sesion"}
    assert cierre_repetido.status_code == 400
    assert cierre_repetido.json() == {"detail": "no_hay_sesión_abierta"}


def test_api_votacion_caracteriza_exitos_y_rechazos():
    with TestClient(app) as client:
        sin_sesion = client.post("/moderacion/abrir_votacion", json=VOTACION)
        client.post("/moderacion/preparar_sesion")
        sesion = sesion_service_module.sesion_service.sesion_actual
        sesion.concejales[1].presente = False
        sesion.concejales[2].presente = False
        client.post("/moderacion/abrir_sesion", json={"numero_sesion": 1})
        sin_quorum = client.post("/moderacion/abrir_votacion", json=VOTACION)
        client.post("/moderacion/cerrar_sesion")

    assert sin_sesion.status_code == 400
    assert sin_sesion.json() == {"detail": "No_hay_sesion_abierta"}
    assert sin_quorum.status_code == 400
    assert sin_quorum.json() == {"detail": "No_hay_quorum"}

    with TestClient(app) as client:
        preparar_y_abrir(client)
        apertura = client.post("/moderacion/abrir_votacion", json=VOTACION)
        segunda = client.post("/moderacion/abrir_votacion", json=VOTACION)
        cierre = client.post("/moderacion/cerrar_votacion")
        cierre_sin_votacion = client.post("/moderacion/cerrar_votacion")
        desempate_sin_empate = client.post("/moderacion/voto_desempate", json=True)

    assert apertura.status_code == 200
    assert apertura.json() == {"messege": "Ok abrir votacion"}
    assert segunda.status_code == 400
    assert segunda.json() == {"detail": "hay_una_votación_abierta"}
    assert cierre.status_code == 200
    assert cierre.json() == {"messege": "Ok cierre votacion"}
    assert cierre_sin_votacion.status_code == 400
    assert cierre_sin_votacion.json() == {"detail": "No hay votación abierta."}
    assert desempate_sin_empate.status_code == 400
    assert desempate_sin_empate.json() == {"detail": "no_hay_votacion_abierta"}


def test_api_desempate_positivo_actualiza_historial_de_votacion():
    with TestClient(app) as client:
        preparar_y_abrir(client)
        sesion_service_module.sesion_service.sesion_actual.concejales[2].presente = False
        assert client.post("/moderacion/abrir_votacion", json=VOTACION).status_code == 200
        assert client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "1"}).json()["aceptada"] is True
        assert client.post("/entradas/tecla", json={"dispositivo": "dev2", "tecla": "3"}).json()["aceptada"] is True
        desempate = client.post("/moderacion/voto_desempate", json=True)
        estado = client.get("/estados/estado_global")

    assert desempate.status_code == 200
    assert desempate.json() == {"messege": "Ok desempate votacion"}
    assert estado.json()["sesion"]["votaciones"][0]["estado"] == "APROBADA"
    assert len(estado.json()["sesion"]["votaciones"][0]["votos"]) == 2


def test_api_uso_de_palabra_caracteriza_cola_turno_y_retiro():
    with TestClient(app) as client:
        client.post("/moderacion/preparar_sesion")
        sin_solicitudes = client.post("/moderacion/otorgar_uso_palabra")
        sin_turno = client.post("/moderacion/quitar_uso_palabra")
        solicitud = client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "7"})
        otorgado = client.post("/moderacion/otorgar_uso_palabra")
        retirado = client.post("/moderacion/quitar_uso_palabra")
        estado = client.get("/estados/estado_global")

    assert sin_solicitudes.status_code == 200
    assert sin_solicitudes.json() == {"en_uso_palabra": None}
    assert sin_turno.status_code == 200
    assert sin_turno.json() == []
    assert solicitud.json()["motivo"] == "tecla_uso_palabra"
    assert otorgado.status_code == 200
    assert otorgado.json()["dni"] == "1"
    assert otorgado.json()["mostrar_test"] is False
    assert retirado.status_code == 200
    assert retirado.json() == []
    assert estado.json()["sesion"]["pedidos_uso_de_palabra"] == []
    assert estado.json()["sesion"]["en_uso_de_palabra"] is None


def test_api_transmision_se_refleja_en_estado_global_e_info_pantallas():
    with TestClient(app) as client:
        sin_recinto_on = client.post("/moderacion/indicador_transmision_on")
        sin_recinto_off = client.post("/moderacion/indicador_transmision_off")
        client.post("/moderacion/preparar_sesion")
        encendida = client.post("/moderacion/indicador_transmision_on")
        refrescar_info_pantallas()
        pantallas_on = client.get("/estados/info_pantallas")
        apagada = client.post("/moderacion/indicador_transmision_off")
        estado = client.get("/estados/estado_global")
        refrescar_info_pantallas()
        pantallas_off = client.get("/estados/info_pantallas")

    assert sin_recinto_on.status_code == sin_recinto_off.status_code == 400
    assert sin_recinto_on.json() == sin_recinto_off.json() == {"detail": "no_hay_recinto_preparado"}
    assert encendida.status_code == 200
    assert encendida.json() == {"messege": "Ok encender indicador transmision en vivo"}
    assert pantallas_on.json()["transmision_en_vivo"] is True
    assert apagada.status_code == 200
    assert apagada.json() == {"messege": "Ok apagar indicador transmision en vivo"}
    assert estado.json()["sesion"]["transmision_en_vivo"] is False
    assert pantallas_off.json()["transmision_en_vivo"] is False


def test_estado_global_caracteriza_presencia_palabra_voto_y_eventos():
    with TestClient(app) as client:
        preparar_y_abrir(client)
        presencia = client.post("/entradas/tecla", json={"dispositivo": "dev3", "tecla": "9"})
        solicitud = client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "7"})
        client.post("/moderacion/otorgar_uso_palabra")
        assert client.post("/moderacion/abrir_votacion", json=VOTACION).status_code == 200
        voto = client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "1"})
        estado = client.get("/estados/estado_global")

    cuerpo = estado.json()
    sesion = cuerpo["sesion"]
    assert presencia.json()["motivo"] == "cambio_presencia"
    assert solicitud.json()["motivo"] == "tecla_uso_palabra"
    assert voto.json()["valor_voto"] == "Positivo"
    assert cuerpo["hay_sesion"] is True
    assert isinstance(cuerpo["eventos"], list) and cuerpo["eventos"]
    assert {"seq", "line"} <= cuerpo["eventos"][-1].keys()
    assert sesion["cantidad_presentes"] == 2
    assert sesion["concejales"][2]["presente"] is False
    assert sesion["en_uso_de_palabra"]["dni"] == "1"
    assert sesion["votaciones"][0]["estado"] == "EN_CURSO"
    assert sesion["votaciones"][0]["votos"][0]["valor_voto"] == "Positivo"
    assert datetime.fromisoformat(sesion["votaciones"][0]["hora_inicio"])


def test_info_pantallas_http_caracteriza_sesion_y_votacion_en_curso_y_cerrada():
    with TestClient(app) as client:
        client.post("/moderacion/preparar_sesion")
        refrescar_info_pantallas()
        preparada = client.get("/estados/info_pantallas")
        client.post("/moderacion/abrir_sesion", json={"numero_sesion": 8})
        client.post("/moderacion/indicador_transmision_on")
        assert client.post("/moderacion/abrir_votacion", json=VOTACION).status_code == 200
        client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "1"})
        refrescar_info_pantallas()
        en_curso = client.get("/estados/info_pantallas")
        client.post("/moderacion/cerrar_votacion")
        refrescar_info_pantallas()
        cerrada = client.get("/estados/info_pantallas")

    assert preparada.status_code == en_curso.status_code == cerrada.status_code == 200
    assert preparada.json()["sesion_abierta"] is False
    assert preparada.json()["numero_sesion"] is None
    assert preparada.json()["hora_inicio_sesion"] is None
    assert preparada.json()["votos_emitidos_votacion_en_curso"] is None
    assert len(preparada.json()["bancas"]) == 3
    assert en_curso.json()["sesion_abierta"] is True
    assert en_curso.json()["numero_sesion"] == 8
    assert en_curso.json()["transmision_en_vivo"] is True
    assert datetime.fromisoformat(en_curso.json()["hora_inicio_sesion"])
    assert en_curso.json()["nro_votacion_en_curso"] == 1
    assert en_curso.json()["votos_emitidos_votacion_en_curso"] == 1
    assert en_curso.json()["bancas"][0]["voto"] == "POSITIVO"
    assert cerrada.json()["estado_votacion"].startswith("Votacion Nº1 INCONCLUSA")
    assert cerrada.json()["votos_emitidos_votacion_en_curso"] == 1
    assert cerrada.json()["bancas"][0]["voto"] == "POSITIVO"
