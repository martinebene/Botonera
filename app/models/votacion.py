from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.sesion_service import SesionService  # solo para type hints

from app.models.voto import Voto, ValorVoto

class EstadosVotacion(Enum):
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    EMPATADA = "EMPATADA"
    EN_CURSO = "EN_CURSO"
    INCONCLUSA = "INCONCLUSA"

class Votacion:
    """
    Representa una votación dentro de una sesión.
    """

    _next_id: int = 1

   
    def __init__(
        self,
        sesion_service: "SesionService",
        numero: int,
        tipo: str,
        tema: str,
        computa_sobre_los_presentes: bool,
        factor_mayoria_especial: int,
        id: Optional[int] = None,
    ) -> None:
        # ID interno en memoria, auto-incremental
        if id is None:
            self.id = Votacion._next_id
            Votacion._next_id += 1
        else:
            self.id = id

        self.sesion_service = sesion_service
        self.estado = EstadosVotacion.EN_CURSO
        self.numero = numero
        self.tipo = tipo
        self.tema = tema
        self.computa_sobre_los_presentes = computa_sobre_los_presentes
        self.factor_mayoria_especial = factor_mayoria_especial
        self.hora_inicio: datetime = datetime.now()
        self.hora_fin: Optional[datetime] = None
        # self.presentes_al_cierre: Optional[int] = None
        self.votos: List[Voto] = []

    def registrar_voto(self, voto: Voto) -> None:
        """
        Agrega un voto a la votación.

        Reglas:
        - La votación debe estar abierta.
        - Solo un voto por concejal.
        """
        if (self.estado != EstadosVotacion.EN_CURSO):
            raise ValueError("votacion_cerrada")

        for v in self.votos:
            if v.concejal.dni == voto.concejal.dni:
                raise ValueError("concejal_ya_voto")

        self.votos.append(voto)

        sesion = self.sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            raise ValueError("no_hay_sesion_abierta")
        presentes = [c for c in sesion.concejales if c.presente]
        dnis_presentes = {c.dni for c in presentes}
        dnis_que_votaron = {v.concejal.dni for v in self.votos}
        if dnis_presentes.issubset(dnis_que_votaron):
            # self.presentes_al_cierre=
            self.cerrar()

    def cerrar(self) -> None:
        """Cierra la votación y registra hora de fin."""
        if (self.estado != EstadosVotacion.EN_CURSO):
            raise ValueError("no_hay_votacion_en_curso")
                
        # sesion = self.sesion_service.obtener_sesion_actual
        # if sesion is None or not sesion.:
        #     raise ValueError("no_hay_sesion_abierta")
        
        votos_positivos = self.contar_votos_por_tipo(ValorVoto.POSITIVO)
        votos_negativos = self.contar_votos_por_tipo(ValorVoto.NEGATIVO)
        votos_abstencion = self.contar_votos_por_tipo(ValorVoto.ABSTENCION)
        votos_emitidos = votos_positivos + votos_negativos + votos_abstencion
        
        if self.factor_mayoria_especial == 0 or self.factor_mayoria_especial is None:
            if votos_positivos > votos_negativos:
                self.estado = EstadosVotacion.APROBADA
            else:
                self.estado = EstadosVotacion.RECHAZADA
            if votos_positivos == votos_negativos:
                self.estado = EstadosVotacion.EMPATADA


        if self.factor_mayoria_especial != 0:
            if self.computa_sobre_los_presentes:
                if votos_positivos/votos_emitidos >= self.factor_mayoria_especial:
                    self.estado = EstadosVotacion.APROBADA
                else:
                    self.estado = EstadosVotacion.RECHAZADA
            else:
                
                if votos_positivos/self.sesion_service.cantidad_concejales_totales() >= self.factor_mayoria_especial:
                    self.estado = EstadosVotacion.APROBADA
                else:
                    self.estado = EstadosVotacion.RECHAZADA

        if (votos_emitidos < self.sesion_service.cantidad_concejales_presentes()) or (votos_emitidos < self.sesion_service.sesion_actual.quorum) or (votos_emitidos==0):
            self.estado = EstadosVotacion.INCONCLUSA
        self.hora_fin = datetime.now()
        

    def desempatar_y_cerrar(self, voto_desempate: Voto):
        if voto_desempate.valor_voto == ValorVoto.POSITIVO:
            self.estado = EstadosVotacion.APROBADA
        else:
            self.estado = EstadosVotacion.RECHAZADA
        self.hora_fin=datetime.now()

    def recalcular_estado_por_cambio_ausencias(self):
        if (self.estado != EstadosVotacion.EN_CURSO):
            raise ValueError("votacion_cerrada")

        sesion = self.sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            raise ValueError("no_hay_sesion_abierta")
        
        presentes = [c for c in sesion.concejales if c.presente]
        dnis_presentes = {c.dni for c in presentes}
        dnis_que_votaron = {v.concejal.dni for v in self.votos}
        if dnis_presentes.issubset(dnis_que_votaron):
            self.cerrar()
        return

    def contar_votos_por_tipo(self, tipo: ValorVoto) -> int:
        n = 0
        for v in self.votos:
            if v.valor_voto is tipo:
                n += 1
        return n

    def to_linea_votos(self) -> str:
        linea = "Votos votacion Nº" + str(self.numero) + "/S" + str(self.sesion_service.sesion_actual.numero_sesion) + ": "

        votos_ordenados = sorted(
            self.votos,
            key=lambda v: (
                (v.concejal.bloque or "").lower(),
                (v.concejal.apellido or "").lower()
            )
        )

        partes = []
        for v in votos_ordenados:
            partes.append(v.concejal.print_corto() + " voto:" + v.valor_voto.value)

        return linea + " - ".join(partes)


    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "numero": self.numero,
            "tipo": self.tipo,
            "tema": self.tema,
            "estado": self.estado.value,
            "computa_sobre_los_presentes": self.computa_sobre_los_presentes,
            "factor_mayoria_especial": self.factor_mayoria_especial,
            "hora_inicio": self.hora_inicio.isoformat(),
            "hora_fin": self.hora_fin.isoformat() if self.hora_fin else None,
            "votos": [v.to_dict() for v in self.votos],
        }
