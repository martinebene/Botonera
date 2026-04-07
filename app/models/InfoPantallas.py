from datetime import datetime, timedelta
from typing import List
from fractions import Fraction
import time

from app.models.sesion import Sesion
from app.models.banca import Banca
from app.models.votacion import Votacion, EstadosVotacion
from app.models.voto import ValorVoto

class InfoPantallas:
    """
    Representa los estados para pantalla de una sesión del Concejo.
    """

    INTERVALO_REFRESCO_MS = 200

    ultimo_refresco: datetime | None
    hora_actual: datetime | None

    sesion: Sesion

    hora_apertura_recinto: datetime | None
    transmision_en_vivo: False
    sesion_abierta: bool
    numero_sesion: int | None
    hora_inicio_sesion: datetime | None
    hora_fin_sesion: datetime | None
    cantidad_presentes: int | None
    diferencia_contra_quorum: int | None
    pedidos_uso_de_palabra: list[str] | None
    bancas: List[Banca]

    votacion: Votacion
    votacion_en_curso: bool
    hora_apertura_votacion: datetime | None
    nro_votacion_en_curso: int | None
    tema_votacion_en_curso: str | None
    tipo_votacion_en_curso: str | None
    computa_sobre_los_presentes: bool
    factor_mayoria_especial: float
    votos_emitidos_votacion_en_curso: int | None
    estado_votacion: str | None
    titulo_votacion: str | None
    ocultar_votos: bool
    
    eventos: list[str] | None

    def __init__(self) -> None:
        self.sesion = None

        self.ultimo_refresco = None
        self.hora_actual = None

        self.hora_apertura_recinto = None
        self.transmision_en_vivo = False
        self.sesion_abierta = None
        self.numero_sesion = None
        self.hora_inicio_sesion = None
        self.hora_fin_sesion = None
        self.cantidad_presentes = None
        self.diferencia_contra_quorum = None
        self.pedidos_uso_de_palabra = []
        self.bancas = []

        self.votacion = None
        self.votacion_en_curso = False
        self.hora_apertura_votacion = None
        self.nro_votacion_en_curso = None
        self.tema_votacion_en_curso = None
        self.tipo_votacion_en_curso = None
        self.votos_emitidos_votacion_en_curso = None
        self.estado_votacion = None
        self.titulo_votacion = None
        self.ocultar_votos = False

        self.eventos = []


    def refrescar(self) -> None:
        ahora = datetime.now()

        if self.ultimo_refresco is not None:
            if ahora - self.ultimo_refresco < timedelta(milliseconds=self.INTERVALO_REFRESCO_MS):
                return

        self.hora_actual = ahora
        
        if (self.sesion):
            self.sesion_abierta = self.sesion.abierta
            self.transmision_en_vivo = self.sesion.transmision_en_vivo
            self.numero_sesion = self.sesion.numero_sesion
            self.hora_inicio_sesion = self.sesion.hora_inicio
            self.hora_fin_sesion = self.sesion.hora_fin
            self.cantidad_presentes = sum(1 for c in self.sesion.concejales if c.presente)
            self.diferencia_contra_quorum = self.cantidad_presentes - self.sesion.quorum

            self.pedidos_uso_de_palabra = [
                c.nombre +" "+ c.apellido for c in self.sesion.pedidos_uso_de_palabra
            ]

            dict_concejales = {c.banca: c for c in self.sesion.concejales}
            for b in self.bancas:
                b.en_uso_palabra = False
                c = dict_concejales.get(b.numero_banca)
                if c:
                    b.presente = c.presente
                    b.test_mode = (time.monotonic() < c.mostrar_test_hasta)
                if (self.sesion.en_uso_de_palabra is not None) and (b.numero_banca == self.sesion.en_uso_de_palabra.banca):
                    b.en_uso_palabra = True

        else:
            self.sesion_abierta = None
            self.numero_sesion = None
            self.hora_inicio_sesion = None
            self.hora_fin_sesion = None
            self.cantidad_presentes = None
            self.diferencia_contra_quorum = None
            self.pedidos_uso_de_palabra = []
            self.bancas = []
        
        
        if (self.votacion):
            self.votos_emitidos_votacion_en_curso = sum(
                1 for voto in self.votacion.votos if voto.valor_voto is not None
            )
            if(self.votacion.estado is EstadosVotacion.EN_CURSO):
                self.estado_votacion="Votacion Nº"+str(self.votacion.numero)+" en curso: "+str(self.votos_emitidos_votacion_en_curso)+" votos emitidos."
            if(self.votacion.estado is EstadosVotacion.APROBADA):
                self.estado_votacion="Votacion Nº"+str(self.votacion.numero)+" APROBADA: "+str(self.votos_emitidos_votacion_en_curso)+" votos ("+str(self.votacion.contar_votos_por_tipo(ValorVoto.POSITIVO))+" Positivos, "+str(self.votacion.contar_votos_por_tipo(ValorVoto.NEGATIVO))+" Negativos y "+str(self.votacion.contar_votos_por_tipo(ValorVoto.ABSTENCION))+ " Abstenciones)"
            if(self.votacion.estado is EstadosVotacion.RECHAZADA):
                self.estado_votacion="Votacion Nº"+str(self.votacion.numero)+" RECHAZADA: "+str(self.votos_emitidos_votacion_en_curso)+" votos ("+str(self.votacion.contar_votos_por_tipo(ValorVoto.POSITIVO))+" Positivos, "+str(self.votacion.contar_votos_por_tipo(ValorVoto.NEGATIVO))+" Negativos y "+str(self.votacion.contar_votos_por_tipo(ValorVoto.ABSTENCION))+ " Abstenciones)"
            if(self.votacion.estado is EstadosVotacion.EMPATADA):
                self.estado_votacion="Votacion Nº"+str(self.votacion.numero)+" EMPATADA: "+str(self.votos_emitidos_votacion_en_curso)+" votos ("+str(self.votacion.contar_votos_por_tipo(ValorVoto.POSITIVO))+" Positivos, "+str(self.votacion.contar_votos_por_tipo(ValorVoto.NEGATIVO))+" Negativos y "+str(self.votacion.contar_votos_por_tipo(ValorVoto.ABSTENCION))+ " Abstenciones)"
            if(self.votacion.estado is EstadosVotacion.INCONCLUSA):
                self.estado_votacion="Votacion Nº"+str(self.votacion.numero)+" INCONCLUSA: "+str(self.votos_emitidos_votacion_en_curso)+" votos ("+str(self.votacion.contar_votos_por_tipo(ValorVoto.POSITIVO))+" Positivos, "+str(self.votacion.contar_votos_por_tipo(ValorVoto.NEGATIVO))+" Negativos y "+str(self.votacion.contar_votos_por_tipo(ValorVoto.ABSTENCION))+ " Abstenciones)"

            for banca in self.bancas:
                banca.voto = None
            
            bancas_por_numero = {b.numero_banca: b for b in self.bancas}

            for voto in self.votacion.votos:
                if voto.concejal is not None:
                    banca = bancas_por_numero.get(voto.concejal.banca)
                    if banca is not None:
                        banca.voto = voto.valor_voto

        else:
            self.hora_apertura_votacion = None
            self.nro_votacion_en_curso = None
            self.tema_votacion_en_curso = None
            self.tipo_votacion_en_curso = None
            self.votos_emitidos_votacion_en_curso = None
            self.computa_sobre_los_presentes = True
            self.factor_mayoria_especial = 0

            for banca in self.bancas:
                banca.voto = None
                

        self.ultimo_refresco = ahora


    def add_sesion(self, sesion:Sesion) -> None:
        self.sesion = sesion
        self.hora_apertura_recinto = sesion.hora_apertura_recinto

        self.bancas = sorted(
            [Banca(c) for c in sesion.concejales],
            key=lambda b: b.numero_banca
            ) 

    def add_votacion(self, votacion:Votacion) -> None:
        self.votacion = votacion
        self.hora_apertura_votacion = votacion.hora_inicio
        self.nro_votacion_en_curso = votacion.numero
        self.tema_votacion_en_curso = votacion.tema
        self.tipo_votacion_en_curso = votacion.tipo
        self.computa_sobre_los_presentes = votacion.computa_sobre_los_presentes
        self.factor_mayoria_especial = votacion.factor_mayoria_especial

        if(votacion.computa_sobre_los_presentes):
            if(votacion.factor_mayoria_especial==0 or None):
                self.titulo_votacion="Nº"+str(votacion.numero)+" de tipo "+votacion.tipo+" sin mayoria especial, sobre presentes"
            else:
                self.titulo_votacion="Nº"+str(votacion.numero)+" de tipo "+votacion.tipo+" con mayoria de " +str(Fraction(votacion.factor_mayoria_especial).limit_denominator(10))+", sobre presentes"
        else:
            if(votacion.factor_mayoria_especial==0 or None):
                self.titulo_votacion="Nº"+str(votacion.numero)+" de tipo "+votacion.tipo+" sin mayoria especial, sobre cuerpo"
            else:
                self.titulo_votacion="Nº"+str(votacion.numero)+" de tipo "+votacion.tipo+" con mayoria de " +str(Fraction(votacion.factor_mayoria_especial).limit_denominator(10))+", sobre cuerpo"

    def clear_votacion(self) -> None:
        self.votacion = None

    def to_dict(self) -> dict:
        return {
            "hora_actual": self.hora_actual.isoformat() if self.hora_actual else None,
            "hora_apertura_recinto": self.hora_apertura_recinto.isoformat() if self.hora_apertura_recinto else None,
            
            "sesion_abierta": self.sesion_abierta,
            "transmision_en_vivo": self.transmision_en_vivo,
            "numero_sesion": self.numero_sesion,
            "hora_inicio_sesion": self.hora_inicio_sesion.isoformat() if self.hora_inicio_sesion else None,
            "hora_fin_sesion": self.hora_fin_sesion.isoformat() if self.hora_fin_sesion else None,
            "cantidad_presentes": self.cantidad_presentes,
            "diferencia_contra_quorum": self.diferencia_contra_quorum,
            "pedidos_uso_de_palabra": self.pedidos_uso_de_palabra,
            "bancas": [b.to_dict() for b in self.bancas],
            "nro_votacion_en_curso": self.nro_votacion_en_curso,
            "hora_apertura_votacion": self.hora_apertura_votacion.isoformat() if self.hora_apertura_votacion else None,
            "tema_votacion_en_curso": self.tema_votacion_en_curso,
            "tipo_votacion_en_curso": self.tipo_votacion_en_curso,
            "votos_emitidos_votacion_en_curso": self.votos_emitidos_votacion_en_curso,
            "estado_votacion": self.estado_votacion,
            "titulo_votacion":self.titulo_votacion,
        }