import pytest

from app.models.votacion import EstadosVotacion
from app.models.voto import ValorVoto, Voto
from app.services import sesion_service as sesion_service_module
from app.services.votacion_service import votacion_service


def abrir_sesion(concejales, presentes=3, quorum=2):
    servicio = sesion_service_module.sesion_service
    sesion = servicio.preparar_sesion()
    for indice, concejal in enumerate(sesion.concejales):
        concejal.presente = indice < presentes
    sesion.quorum = quorum
    servicio.abrir_sesion(1)
    return sesion


def abrir_votacion(sesion, factor=0, sobre_presentes=True):
    return votacion_service.abrir_votacion(1, "Ordinaria", "Tema", sobre_presentes, factor)


def votar(votacion, concejal, valor):
    votacion_service.registrar_voto(Voto(concejal, valor))


def test_abrir_votacion_requiere_sesion_abierta_y_quorum(concejales):
    with pytest.raises(ValueError, match="No_hay_sesion_abierta"):
        abrir_votacion(None)

    sesion = abrir_sesion(concejales, presentes=1, quorum=2)
    with pytest.raises(ValueError, match="No_hay_quorum"):
        abrir_votacion(sesion)


def test_abrir_votacion_rechaza_otra_en_curso(concejales):
    sesion = abrir_sesion(concejales)
    abrir_votacion(sesion)
    with pytest.raises(ValueError, match="hay_una_votación_abierta"):
        abrir_votacion(sesion)


def test_registra_voto_y_rechaza_duplicado(concejales):
    sesion = abrir_sesion(concejales)
    votacion = abrir_votacion(sesion)
    votar(votacion, sesion.concejales[0], ValorVoto.POSITIVO)

    with pytest.raises(ValueError, match="concejal_ya_voto"):
        votar(votacion, sesion.concejales[0], ValorVoto.NEGATIVO)


@pytest.mark.parametrize(
    ("votos", "estado"),
    [
        ([ValorVoto.POSITIVO, ValorVoto.POSITIVO, ValorVoto.POSITIVO], EstadosVotacion.APROBADA),
        ([ValorVoto.NEGATIVO, ValorVoto.NEGATIVO, ValorVoto.ABSTENCION], EstadosVotacion.RECHAZADA),
        ([ValorVoto.POSITIVO, ValorVoto.NEGATIVO, ValorVoto.ABSTENCION], EstadosVotacion.EMPATADA),
    ],
)
def test_cierre_automatico_y_mayoria_simple(concejales, votos, estado):
    sesion = abrir_sesion(concejales)
    votacion = abrir_votacion(sesion)
    for concejal, valor in zip(sesion.concejales, votos):
        votar(votacion, concejal, valor)

    assert votacion.estado is estado
    assert votacion.hora_fin is not None
    assert votacion_service.votacion_actual is (votacion if estado is EstadosVotacion.EMPATADA else None)


def test_mayoria_especial_se_calcula_sobre_votos_emitidos_y_total_del_cuerpo(concejales):
    sesion = abrir_sesion(concejales)
    votacion = abrir_votacion(sesion, factor=2 / 3, sobre_presentes=True)
    for concejal, valor in zip(sesion.concejales, [ValorVoto.POSITIVO, ValorVoto.POSITIVO, ValorVoto.ABSTENCION]):
        votar(votacion, concejal, valor)
    assert votacion.estado is EstadosVotacion.APROBADA

    votacion = abrir_votacion(sesion, factor=2 / 3, sobre_presentes=False)
    for concejal, valor in zip(sesion.concejales, [ValorVoto.POSITIVO, ValorVoto.POSITIVO, ValorVoto.NEGATIVO]):
        votar(votacion, concejal, valor)
    assert votacion.estado is EstadosVotacion.APROBADA


def test_cierre_forzado_sin_votos_es_inconcluso(concejales):
    sesion = abrir_sesion(concejales)
    votacion = abrir_votacion(sesion)

    cerrada = votacion_service.cierre_forzado()

    assert cerrada.estado is EstadosVotacion.INCONCLUSA
    assert votacion_service.votacion_actual is None


def test_cierre_forzado_con_votos_incompletos_es_inconcluso(concejales):
    sesion = abrir_sesion(concejales)
    votacion = abrir_votacion(sesion)
    votar(votacion, sesion.concejales[0], ValorVoto.POSITIVO)
    votar(votacion, sesion.concejales[1], ValorVoto.NEGATIVO)

    cerrada = votacion_service.cierre_forzado()

    assert cerrada.estado is EstadosVotacion.INCONCLUSA


def test_cambio_de_presencia_puede_cerrar_votacion(concejales):
    sesion = abrir_sesion(concejales)
    votacion = abrir_votacion(sesion)
    votar(votacion, sesion.concejales[0], ValorVoto.POSITIVO)
    sesion.concejales[1].presente = False
    sesion.concejales[2].presente = False

    votacion_service.recalcular_cierre_por_cambio_en_presencia()

    assert votacion.estado is EstadosVotacion.INCONCLUSA


@pytest.mark.parametrize(
    ("valor", "estado"),
    [(ValorVoto.POSITIVO, EstadosVotacion.APROBADA), (ValorVoto.NEGATIVO, EstadosVotacion.RECHAZADA)],
)
def test_desempate_positivo_y_negativo(concejales, valor, estado):
    sesion = abrir_sesion(concejales, presentes=2)
    votacion = abrir_votacion(sesion)
    votar(votacion, sesion.concejales[0], ValorVoto.POSITIVO)
    votar(votacion, sesion.concejales[1], ValorVoto.NEGATIVO)

    cerrada = votacion_service.voto_desempate(Voto(None, valor))

    assert cerrada.estado is estado
    assert votacion_service.votacion_actual is None


def test_desempate_rechaza_votacion_no_empatada(concejales):
    sesion = abrir_sesion(concejales)
    abrir_votacion(sesion)
    with pytest.raises(ValueError, match="no_hay_votacion_abierta"):
        votacion_service.voto_desempate(Voto(None, ValorVoto.POSITIVO))
