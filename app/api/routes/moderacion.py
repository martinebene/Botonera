from fastapi import APIRouter, HTTPException, Body

from app.services.sesion_service import sesion_service
from app.models.sesion import Sesion

from app.services.votacion_service import votacion_service
from app.models.votacion import Votacion
from app.models.voto import Voto, ValorVoto


router = APIRouter(
    prefix="/moderacion",
    tags=["moderacion"],
)


@router.post("/abrir_sesion")
def abrir_sesion(
    numero_sesion: int = Body(..., embed=True),
):
    """
    Endpoint para ABRIR una sesión.

    Body esperado:
        { "numero_sesion": 52 }
    """

    try:
        sesion: Sesion = sesion_service.abrir_sesion(numero_sesion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sesion.to_dict()


@router.post("/cerrar_sesion")
def cerrar_sesion():
    """
    Endpoint para CERRAR la sesión actual.
    """
    try:
        sesion: Sesion = sesion_service.cerrar_sesion()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return sesion.to_dict()


@router.post("/otorgar_uso_palabra")
def otorgar_uso_palabra():
    """
    Endpoint para otorgar el uso de la palabra.
    """
    try:
        sesion: Sesion = sesion_service.otorgar_uso_palabra()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if sesion_service.sesion_actual.en_uso_de_palabra is not None:
        return sesion_service.sesion_actual.en_uso_de_palabra.to_dict()
    else:
        return {
        "ven_uso_palabra": None
    }


@router.post("/quitar_uso_palabra")
def quitar_uso_palabra():
    """
    Endpoint para quitar el uso de la palabra.
    """
    try:
        sesion: Sesion = sesion_service.quitar_uso_palabra()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [d.to_dict() for d in sesion_service.sesion_actual.pedidos_uso_de_palabra]


@router.post("/abrir_votacion")
def abrir_votacion(
    numero: int = Body(...),
    tipo: str = Body(...),
    tema: str = Body(...),
    computa_sobre_los_presentes: bool = Body(...),
    factor_mayoria_especial: float = Body(...), #0 para mayoria simple
):
    """
    Abre una nueva votación en la sesión en curso.

    Body esperado:
    {
      "numero": 1,
      "tipo": "ordinaria",
      "tema": "Aprobación del presupuesto"
      "computa_sobre_los_presentes": true
      "factor_mayoria_especial": 0.66
    }
    """
    try:
        votacion: Votacion = votacion_service.abrir_votacion(numero=numero, tipo=tipo, tema=tema, computa_sobre_los_presentes=computa_sobre_los_presentes, factor_mayoria_especial=factor_mayoria_especial)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return votacion.to_dict()


@router.post("/cerrar_votacion")
def cerrar_votacion_forzado():
    """
    Fuerza el cierre de la votación actual.

    Si hay concejales presentes que no votaron, quedan registrados
    en el log del sistema.
    """
    try:
        votacion = votacion_service.cierre_forzado()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "votacion": votacion.to_dict(),
        "cerrada_forzada": True,
    }

@router.post("/voto_desempate")
def voto_desempate(valor_voto: bool = Body(...),):
    """
    si hay votacion abierta y empatada, procesa el voto de desempate
    """
    if valor_voto:
        voto = Voto(concejal=None, valor_voto=ValorVoto.POSITIVO)
    else:
        voto = Voto(concejal=None, valor_voto=ValorVoto.NEGATIVO)

    try:
        votacion=votacion_service.voto_desempate(voto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "votacion": votacion.to_dict(),
        "cerrada_desempate": True,
    }