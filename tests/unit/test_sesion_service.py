import pytest

from app.services import sesion_service as sesion_service_module
from app.services.votacion_service import votacion_service


def test_preparar_sesion_carga_concejales_y_configuracion():
    sesion = sesion_service_module.sesion_service.preparar_sesion()

    assert sesion.abierta is False
    assert sesion.quorum == 2
    assert len(sesion.concejales) == 3
    assert sesion_service_module.sesion_service.sesion_actual is sesion


def test_preparar_sesion_rechaza_una_sesion_ya_preparada():
    servicio = sesion_service_module.sesion_service
    servicio.preparar_sesion()

    with pytest.raises(ValueError, match="ya_hay_sesión_preparada"):
        servicio.preparar_sesion()


def test_preparar_sesion_caracteriza_errores_de_archivo_y_lista_vacia(monkeypatch):
    servicio = sesion_service_module.sesion_service
    monkeypatch.setattr(
        sesion_service_module,
        "cargar_concejales_desde_archivo",
        lambda _ruta: (_ for _ in ()).throw(FileNotFoundError()),
    )
    with pytest.raises(ValueError, match="no_hay_archivo_concejales"):
        servicio.preparar_sesion()

    monkeypatch.setattr(sesion_service_module, "cargar_concejales_desde_archivo", lambda _ruta: [])
    with pytest.raises(ValueError, match="lista_concejales_vacía"):
        servicio.preparar_sesion()


def test_abrir_y_cerrar_sesion_y_limpia_referencia():
    servicio = sesion_service_module.sesion_service
    servicio.preparar_sesion()
    servicio.abrir_sesion(12)

    cerrada = servicio.cerrar_sesion()

    assert cerrada.numero_sesion == 12
    assert cerrada.abierta is False
    assert cerrada.hora_fin is not None
    assert servicio.sesion_actual is None


def test_abrir_sesion_rechaza_sin_recinto_y_sesion_ya_abierta():
    servicio = sesion_service_module.sesion_service
    with pytest.raises(ValueError, match="no_hay_recinto_preparado"):
        servicio.abrir_sesion(1)

    servicio.preparar_sesion()
    servicio.abrir_sesion(1)
    with pytest.raises(ValueError, match="ya_hay_sesión_abierta"):
        servicio.abrir_sesion(2)


def test_cerrar_sesion_rechaza_sin_sesion_abierta():
    with pytest.raises(ValueError, match="no_hay_sesión_abierta"):
        sesion_service_module.sesion_service.cerrar_sesion()

    sesion_service_module.sesion_service.preparar_sesion()
    with pytest.raises(ValueError, match="no_hay_sesión_abierta"):
        sesion_service_module.sesion_service.cerrar_sesion()


def test_cerrar_sesion_fuerza_cierre_de_votacion_en_curso():
    servicio = sesion_service_module.sesion_service
    servicio.preparar_sesion()
    servicio.abrir_sesion(1)
    votacion = votacion_service.abrir_votacion(1, "Ordinaria", "Tema", True, 0)

    servicio.cerrar_sesion()

    assert votacion.hora_fin is not None
    assert votacion_service.votacion_actual is None


def test_presencia_totales_palabra_y_transmision():
    servicio = sesion_service_module.sesion_service
    sesion = servicio.preparar_sesion()
    primero, segundo, _ = sesion.concejales
    segundo.presente = False

    assert servicio.cantidad_concejales_presentes() == 2
    assert servicio.cantidad_concejales_totales() == 3

    servicio.encolar_uso_palabra(primero)
    servicio.encolar_uso_palabra(segundo)
    servicio.encolar_uso_palabra(segundo)
    servicio.otorgar_uso_palabra()
    assert sesion.en_uso_de_palabra is primero
    assert list(sesion.pedidos_uso_de_palabra) == []
    servicio.quitar_uso_palabra()
    assert sesion.en_uso_de_palabra is None

    servicio.encender_indicador_transmision_en_vivo()
    assert sesion.transmision_en_vivo is True
    servicio.apagar_indicador_transmision_en_vivo()
    assert sesion.transmision_en_vivo is False


def test_indicadores_de_transmision_requieren_recinto_preparado():
    servicio = sesion_service_module.sesion_service

    with pytest.raises(ValueError, match="no_hay_recinto_preparado"):
        servicio.encender_indicador_transmision_en_vivo()
    with pytest.raises(ValueError, match="no_hay_recinto_preparado"):
        servicio.apagar_indicador_transmision_en_vivo()
