import json

from typing import List, Optional, TYPE_CHECKING

from app.config import settings
from app.utils import logging
from app.models.sesion import Sesion
from app.models.concejal import Concejal
from app.services.concejal_service import cargar_concejales_desde_archivo

if TYPE_CHECKING:
    from app.models.votacion import Votacion, EstadosVotacion
from app.models.votacion import EstadosVotacion






class SesionService:
    """
    Servicio de dominio para manejar la sesión del Concejo.

    - Mantiene una ÚNICA sesión en memoria (sesion_actual).
    - Abre/cierra sesión.
    - Registra en log aperturas, cierres y aperturas fallidas.
    """

    def __init__(self) -> None:
        self.sesion_actual: Optional[Sesion] = None

    def abrir_sesion(self, numero_sesion: int) -> Sesion:
        """
        Abre una nueva sesión.

        Reglas:
        - Si ya hay sesión abierta -> ValueError + log de APERTURA_FALLIDA.
        - Si falta archivo de concejales -> ValueError + log de APERTURA_FALLIDA.
        - Si la lista de concejales está vacía -> ValueError + log de APERTURA_FALLIDA.
        """

        # Ya hay sesión abierta
        if self.sesion_actual is not None and self.sesion_actual.abierta:
            logging.log_internal("SESION",2, "Rechazo de apertura de sesion porque ya hay sesion abierta")
            raise ValueError("ya_hay_sesión_abierta")

        # Cargamos concejales ANTES de crear la sesión
        try:
            concejales: List[Concejal] = cargar_concejales_desde_archivo(settings.concejales_file)
        except FileNotFoundError:
            logging.log_internal("SESION",2, "Rechazo de apertura de sesion porque no hay archivo de concejales")
            raise ValueError("no_hay_archivo_concejales")

        if not concejales:
            logging.log_internal("SESION",2, "Rechazo de apertura de sesion porque no hay concejales en el archivo")
            raise ValueError("lista_concejales_vacía")

        # Si todo está bien, creamos la sesión
        sesion = Sesion(numero_sesion=numero_sesion)
        sesion.concejales = concejales
        sesion.presentes
        sesion.quorum = settings.quorum
        sesion.disposicion_bancas = json.dumps(settings.disposicion_bancas, indent=2)
        

        self.sesion_actual = sesion

        # Log de apertura exitosa
        logging.log_internal("SESION",3, "Apertura de sesion Nº" + str(self.sesion_actual.numero_sesion))
        return sesion

    def cerrar_sesion(self) -> Sesion:
        """
        Cierra la sesión actual.

        Reglas:
        - Si no hay sesión -> ValueError + log de CIERRE_FALLIDA.
        - Si ya está cerrada -> ValueError + log de CIERRE_FALLIDA.
        - Si se cierra correctamente -> log de CIERRE_OK.
        """

        from app.services.votacion_service import votacion_service

        if self.sesion_actual is None:
            logging.log_internal("SESION",2, "Cierre de sesion fallido porque no hay sesion abierta")
            raise ValueError("ya_hay_sesión_abierta")

        sesion = self.sesion_actual

        if not sesion.abierta:
            logging.log_internal("SESION",2, "Cierre de sesion fallido porque no hay sesion abierta")
            raise ValueError("ya_hay_sesión_abierta")

        
        votacion: Votacion = votacion_service.obtener_votacion_actual()
        if ( (votacion is not None)):
             if(votacion.estado is EstadosVotacion.EN_CURSO):
                votacion_service.cierre_forzado()

        sesion.cerrar() 
 
        # Log de cierre exitoso
        logging.log_internal("SESION",3, "Cierre de sesion Nº" + str(self.sesion_actual.numero_sesion))

        # Dejamos la referencia en None (o podríamos solo dejar la Sesion cerrada)
        self.sesion_actual = None

        return sesion


    def obtener_sesion_actual(self) -> Optional[Sesion]:
        """Devuelve la sesión actual (o None si no hay)."""
        return self.sesion_actual

#metodos de uso de la palabra

    def encolar_uso_palabra(self, concejal: Concejal) -> None:
        """Encola o Desencola un concejal"""
        if concejal not in self.sesion_actual.pedidos_uso_de_palabra:
            self.sesion_actual.pedidos_uso_de_palabra.append(concejal)
            logging.log_internal("PALABRA",3, concejal.print_corto() + " pidio la palabra")
        else:
            self.sesion_actual.pedidos_uso_de_palabra.remove(concejal)
            logging.log_internal("PALABRA",3, concejal.print_corto() + " retiro el pedido la palabra")

    def otorgar_uso_palabra(self) -> None:
        if self.sesion_actual.pedidos_uso_de_palabra:
            self.sesion_actual.en_uso_de_palabra=self.sesion_actual.pedidos_uso_de_palabra.popleft()
            logging.log_internal("PALABRA",3, "Se otorgo uso de la palabra a "+ self.sesion_actual.en_uso_de_palabra.print_corto())
        else:
            self.sesion_actual.en_uso_de_palabra=None
            logging.log_internal("PALABRA",2, "Fallo dar uso de la palabra, porque no hay solicitudes en cola")

    def quitar_uso_palabra(self) -> None:
            s = self.sesion_actual.en_uso_de_palabra.print_corto()
            self.sesion_actual.en_uso_de_palabra=None
            logging.log_internal("PALABRA",3, "Se quito el uso de la palabra a "+ s)

# metodos de concejales:

    def cantidad_concejales_presentes(self) -> int:
            return sum(1 for c in self.sesion_actual.concejales if c.presente)
    
    def cantidad_concejales_totales(self) -> int:
            return len(self.sesion_actual.concejales)

# Instancia única (singleton simple) a usar en toda la app
sesion_service = SesionService()
