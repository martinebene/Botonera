from datetime import datetime, timedelta
from typing import List

from app.models.sesion import Sesion
from app.models.banca import Banca
from app.models.votacion import Votacion


class InfoPantallas:
    """
    Representa los estados para pantalla de una sesión del Concejo.
    """

    INTERVALO_REFRESCO_MS = 200

    ultimo_refresco: datetime | None
    hora_actual: datetime | None

    sesion: Sesion

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
    votos_emitidos_votacion_en_curso: int | None
    ocultar_votos: bool
    
    eventos: list[str] | None

    def __init__(self) -> None:
        self.sesion = None

        self.ultimo_refresco = None
        self.hora_actual = None

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
            self.numero_sesion = self.sesion.numero_sesion
            self.hora_inicio_sesion = self.sesion.hora_inicio
            self.hora_fin_sesion = self.sesion.hora_fin
            self.cantidad_presentes = sum(1 for c in self.sesion.concejales if c.presente)
            self.diferencia_contra_quorum = self.cantidad_presentes - self.sesion.quorum

            self.pedidos_uso_de_palabra = [
                f"{c.nombre} {c.apellido}"
                for c in self.sesion.concejales
                if getattr(c, "en_uso_de_palabra", False)
            ]

            self.bancas = [Banca(c) for c in self.sesion.concejales]
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
            self.hora_apertura_votacion = self.votacion.hora_inicio
            self.nro_votacion_en_curso = self.votacion.numero
            self.tema_votacion_en_curso = self.votacion.tema
            self.tipo_votacion_en_curso = self.votacion.tipo
            self.votos_emitidos_votacion_en_curso = sum(
                1 for voto in self.votacion.votos if voto.valor_voto is not None
            )

        else:
            self.hora_apertura_votacion = None
            self.nro_votacion_en_curso = None
            self.tema_votacion_en_curso = None
            self.tipo_votacion_en_curso = None
            self.votos_emitidos_votacion_en_curso = None

        self.ultimo_refresco = ahora


    def add_sesion(self, sesion:Sesion) -> None:
        self.sesion = sesion
    
        self.bancas = sorted(
            [Banca(c) for c in sesion.concejales],
            key=lambda b: b.numero_banca
            ) 

    def add_votacion(self, votacion:Votacion) -> None:
        self.votacion = votacion
        


    def to_dict(self) -> dict:
        return {
            "hora_actual": self.hora_actual.isoformat() if self.hora_actual else None,
            "sesion_abierta": self.sesion_abierta,
            "numero_sesion": self.numero_sesion,
            "hora_inicio_sesion": self.hora_inicio_sesion.isoformat() if self.hora_inicio_sesion else None,
            "hora_fin_sesion": self.hora_fin_sesion.isoformat() if self.hora_fin_sesion else None,
            "cantidad_presentes": self.cantidad_presentes,
            "diferencia_contra_quorum": self.diferencia_contra_quorum,
            "pedidos_uso_de_palabra": self.pedidos_uso_de_palabra,
            "bancas": [b.to_dict() for b in self.bancas],
            "nro_votacion_en_curso": self.nro_votacion_en_curso,
            "tema_votacion_en_curso": self.tema_votacion_en_curso,
            "tipo_votacion_en_curso": self.tipo_votacion_en_curso,
            "votos_emitidos_votacion_en_curso": self.votos_emitidos_votacion_en_curso,
        }