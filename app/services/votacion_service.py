from __future__ import annotations


from typing import Optional, TYPE_CHECKING

from app.services.sesion_service import sesion_service
from app.models.votacion import Votacion, EstadosVotacion
from app.models.voto import Voto, ValorVoto

from app.utils import logging

class VotacionService:
    """
    Servicio para manejar la votación actual dentro de la sesión.

    - Solo puede haber una votación abierta por sesión.
    - Usa sesion_service para acceder a la sesión actual.
    """

    def __init__(self) -> None:
        self.votacion_actual: Optional[Votacion] = None

    # ------------------------------------------------------------------
    # Métodos privados de apoyo
    # ------------------------------------------------------------------

    # def _calcular_auto_cierre(self, sesion, votacion) -> bool:
    # """
    # Devuelve True si, con el estado ACTUAL de presentes y votos,
    # corresponde cerrar automáticamente la votación.

    # Regla: todos los concejales presentes ya votaron.
    # """
    # presentes = [c for c in sesion.concejales if c.presente]
    # dnis_presentes = {c.dni for c in presentes}
    # dnis_que_votaron = {v.concejal.dni for v in votacion.votos}

    # return dnis_presentes.issubset(dnis_que_votaron)

    # def _cerrar_automaticamente(self, sesion, votacion) -> None:
    #     """
    #     Ejecuta el cierre automático de la votación:
    #     - marca hora_fin
    #     - loguea cierre automático
    #     - borra votacion_actual
    #     """
    #     logging.log_internal("VOTACION",3,"Votacion completada")
    #     votacion.cerrar()

    #     if self.votacion_actual.estado != EstadosVotacion.EMPATADA:
    #         logging.log_internal("VOTACION",3,"Resultado: "+ self.votacion_actual.estado.value+" - VOTOS: " + self.votacion_actual.to_linea_votos())
    #         logging.log_internal("VOTACION",2,"Cierre automatico por completar voto de los presentes")
    #         self.votacion_actual = None
    #     else:
    #         logging.log_internal("VOTACION",3,"Resultado: "+ self.votacion_actual.estado.value+" - Se espera voto de desempate")

    # ------------------------------------------------------------------
    # API pública del servicio
    # ------------------------------------------------------------------

    def abrir_votacion(self, numero: int, tipo: str, tema: str, computa_sobre_los_presentes: bool, factor_mayoria_especial: float) -> Votacion:
        """
        Abre una nueva votación en la sesión actual.
        """


        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            logging.log_internal("VOTACION",2,"Fallo apertura de votacion al no haber sesion activa")
            raise ValueError("No_hay_sesion_abierta")

        if sesion_service.cantidad_concejales_presentes() < sesion.quorum:
            logging.log_internal("VOTACION",2,"Falta quorum para abruir votacion")
            raise ValueError("No_hay_quorum")

        if self.votacion_actual is not None and (self.votacion_actual.estado == EstadosVotacion.EN_CURSO):
            logging.log_internal("VOTACION",2,"Fallo apertura de votacion al ya haber una votacion activa")
            raise ValueError("hay_una_votación_abierta")

        votacion = Votacion(sesion_service=sesion_service ,numero=numero, tipo=tipo, tema=tema, computa_sobre_los_presentes=computa_sobre_los_presentes, factor_mayoria_especial=factor_mayoria_especial)
        sesion.votaciones.append(votacion)
        self.votacion_actual = votacion

        logging.log_internal("VOTACION",3,"Apertura de votacion de tipo " + votacion.tipo + " Nº" + str(votacion.numero) +" con tema: " + votacion.tema)

        return votacion

    def registrar_voto(self, voto: Voto):
        """
        Registra el voto de un concejal en la votación actual.

        Devuelve: (votacion, auto_cerrada: bool)

        Se asume que:
        - hay sesión abierta
        - hay votación abierta
        - el concejal es válido y está presente

        Esas validaciones se hacen en la capa de entrada (input_service).
        """


        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            logging.log_internal("VOTO",2,"Fallo registro de voto al no haber sesion activa")
            raise ValueError("no_hay_sesion_abierta")

        if self.votacion_actual is None or (self.votacion_actual.estado != EstadosVotacion.EN_CURSO):
            logging.log_internal("VOTO",2,"Fallo registro de voto al no haber votacion activa")
            raise ValueError("no_hay_votacion_abierta")

        votacion = self.votacion_actual

        # Puede levantar ValueError("votacion_cerrada" o "concejal_ya_voto")
        votacion.registrar_voto(voto)
        logging.log_internal("VOTO",3,voto.concejal.print_corto() + " voto: "+voto.valor_voto.value)

        # Si corresponde, cerrar y loguear el cierre automático
        if (votacion.estado is not EstadosVotacion.EN_CURSO):
            logging.log_internal("VOTACION",3, "Votacion Nº"+str(votacion.numero)+" completada. Resultado: "+votacion.estado.value+" - Votos: "+str(len(votacion.votos))+" de "+str(len(sesion.concejales))+" - "+str(votacion.contar_votos_por_tipo(ValorVoto.POSITIVO))+" Positivos, "+str(votacion.contar_votos_por_tipo(ValorVoto.NEGATIVO))+" Negativos y "+str(votacion.contar_votos_por_tipo(ValorVoto.ABSTENCION))+ " Abstenciones")
            if (votacion.estado is not EstadosVotacion.EMPATADA):
                self.votacion_actual=None

        return

    def recalcular_cierre_por_cambio_en_presencia(self):
        """
        Se llama cuando cambia el estado presente/ausente de algún concejal
        (por ejemplo, con la tecla 7).
        """
        if self.votacion_actual is None or (self.votacion_actual.estado != EstadosVotacion.EN_CURSO):
            raise ValueError("No hay votación abierta.")

        votacion = self.votacion_actual
        votacion.recalcular_estado_por_cambio_ausencias()


    def cierre_forzado(self) -> Votacion:
        """
        Fuerza el cierre de la votación actual.
        """

        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            raise ValueError("No hay sesión abierta.")

        if self.votacion_actual is None or (self.votacion_actual.estado != EstadosVotacion.EN_CURSO):
            raise ValueError("No hay votación abierta.")

        votacion = self.votacion_actual

        presentes = [c for c in sesion.concejales if c.presente]
        dnis_que_votaron = {v.concejal.dni for v in votacion.votos}
        concejales_sin_voto = [c for c in presentes if c.dni not in dnis_que_votaron]

        votacion.cerrar()
        logging.log_internal("VOTACION",3, "Cierre forzado - sin votar: "+str(concejales_sin_voto))

        self.votacion_actual = None

        return votacion

    def obtener_votacion_actual(self) -> Optional[Votacion]:
        return self.votacion_actual


    def voto_desempate(self, voto: Voto) -> Votacion:
        """
        Registra el voto desempate de la votación actual.

        Devuelve: (votacion)

        Se asume que:
        - hay sesión abierta
        - hay votación abierta

        Esas validaciones se hacen en la capa de entrada (input_service).
        """

        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            logging.log_internal("VOTO",2,"Desempate fallo registro de voto al no haber sesion activa")
            raise ValueError("no_hay_sesion_abierta")

        if self.votacion_actual is None or (self.votacion_actual.estado != EstadosVotacion.EMPATADA):
            logging.log_internal("VOTO",2,"Desempate fallo registro de voto al no haber votacion a desempatar")
            raise ValueError("no_hay_votacion_abierta")

        votacion = self.votacion_actual

        votacion.desempatar_y_cerrar(voto)
        logging.log_internal("VOTACION",3, "Votacion Nº"+str(votacion.numero)+" DESEMPATADA. Resultado: "+votacion.estado.value+" - Votos: "+str(len(votacion.votos))+" de "+str(len(sesion.concejales))+" - "+str(votacion.contar_votos_por_tipo(ValorVoto.POSITIVO))+" Positivos, "+str(votacion.contar_votos_por_tipo(ValorVoto.NEGATIVO))+" Negativos y "+str(votacion.contar_votos_por_tipo(ValorVoto.ABSTENCION))+ " Abstenciones")
        self.votacion_actual = None

        return votacion

# Instancia única del servicio a importar desde otras partes
votacion_service = VotacionService()
