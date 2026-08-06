from fastapi.testclient import TestClient

from app.main import app
from app.services import sesion_service as sesion_service_module


def test_aplicacion_y_estados_sin_sesion():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        global_ = client.get("/estados/estado_global")
        pantallas = client.get("/estados/info_pantallas")
        configuracion = client.get("/estados/configuracion")

    assert global_.json()["hay_sesion"] is False
    assert global_.json()["sesion"] is None
    assert "bancas" in pantallas.json()
    assert {"version", "quorum", "disposicion_bancas"} <= configuracion.json().keys()


def test_api_prepara_abre_y_cierra_sesion_y_expone_estado_serializado():
    with TestClient(app) as client:
        assert client.post("/moderacion/preparar_sesion").status_code == 200
        preparada = client.get("/estados/estado_global").json()
        assert client.post("/moderacion/abrir_sesion", json={"numero_sesion": 5}).status_code == 200
        abierta = client.get("/estados/estado_global").json()
        assert client.post("/moderacion/cerrar_sesion").status_code == 200

    assert preparada["sesion"]["abierta"] is False
    assert abierta["sesion"]["numero_sesion"] == 5
    assert abierta["sesion"]["en_uso_de_palabra"] is None


def test_api_entrada_rechaza_sin_sesion_y_acepta_presencia_preparada():
    with TestClient(app) as client:
        sin_sesion = client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "9"})
        client.post("/moderacion/preparar_sesion")
        preparada = client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "9"})

    assert sin_sesion.status_code == 200
    assert sin_sesion.json()["motivo"] == "no_hay_sesion_abierta"
    assert preparada.json()["motivo"] == "cambio_presencia"


def test_api_abre_y_cierra_votacion_y_desempate():
    with TestClient(app) as client:
        client.post("/moderacion/preparar_sesion")
        client.post("/moderacion/abrir_sesion", json={"numero_sesion": 1})
        apertura = client.post(
            "/moderacion/abrir_votacion",
            json={
                "numero": 1,
                "tipo": "Ordinaria",
                "tema": "Tema",
                "computa_sobre_los_presentes": True,
                "factor_mayoria_especial": 0,
            },
        )
        cierre = client.post("/moderacion/cerrar_votacion")
        desempate = client.post("/moderacion/voto_desempate", json=True)

    assert apertura.status_code == 200
    assert cierre.status_code == 200
    assert desempate.status_code == 400
    assert desempate.json()["detail"] == "no_hay_votacion_abierta"


def test_api_expone_votacion_en_curso_y_acepta_desempate_positivo():
    with TestClient(app) as client:
        client.post("/moderacion/preparar_sesion")
        sesion = sesion_service_module.sesion_service.sesion_actual
        sesion.concejales[2].presente = False
        client.post("/moderacion/abrir_sesion", json={"numero_sesion": 1})
        client.post(
            "/moderacion/abrir_votacion",
            json={
                "numero": 1,
                "tipo": "Ordinaria",
                "tema": "Tema",
                "computa_sobre_los_presentes": True,
                "factor_mayoria_especial": 0,
            },
        )
        client.post("/entradas/tecla", json={"dispositivo": "dev1", "tecla": "1"})
        en_curso = client.get("/estados/estado_global")
        client.post("/entradas/tecla", json={"dispositivo": "dev2", "tecla": "3"})
        desempate = client.post("/moderacion/voto_desempate", json=True)

    assert en_curso.status_code == 200
    assert en_curso.json()["sesion"]["votaciones"][0]["estado"] == "EN_CURSO"
    assert desempate.status_code == 200
    assert desempate.json()["messege"] == "Ok desempate votacion"


def test_estado_global_http_serializa_concejal_en_uso_de_palabra():
    with TestClient(app) as client:
        client.post("/moderacion/preparar_sesion")
        sesion = sesion_service_module.sesion_service.sesion_actual
        sesion_service_module.sesion_service.encolar_uso_palabra(sesion.concejales[0])
        client.post("/moderacion/otorgar_uso_palabra")
        respuesta = client.get("/estados/estado_global")

    concejal = respuesta.json()["sesion"]["en_uso_de_palabra"]
    assert respuesta.status_code == 200
    assert concejal["dni"] == "1"
