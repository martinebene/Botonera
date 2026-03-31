from typing import Optional, TYPE_CHECKING

from app.models.sesion import Sesion
from app.models.votacion import Votacion
from app.utils import logging

from app.models.InfoPantallas import InfoPantallas




class InfoPantallasService:
    """
    Servicio de dominio para manejar la pantalla del Concejo.

    - Mantiene un ÚNICO servicio de pantalla en memoria (pantalla_actual).

    """

    def __init__(self) -> None:
        self.info_pantallas_actual: Optional[InfoPantallas] = None

    def crea_info_pantallas(self) -> InfoPantallas:


        # Ya hay infoPantallas
        if self.info_pantallas_actual is not None:
            logging.log_internal("BACKEND",1, "Rechazo de apertura de infoPantallas porque ya existe una instancia")
            raise ValueError("ya_hay_info_pantallas")


        # Si todo está bien, creamos la info_pantalla
        info_pantallas = InfoPantallas()

        self.info_pantallas_actual = info_pantallas

        # Log de apertura exitosa
        logging.log_internal("BACKEND",1, "Apertura de InfoPantallas")
        return info_pantallas


    def obtener_info_pantallas(self) -> Optional[InfoPantallas]:
        """Devuelve la infoPantallas actual."""
        if self.info_pantallas_actual is None:
            self.crea_info_pantallas()

        self.info_pantallas_actual.refrescar()

        return self.info_pantallas_actual


    def add_sesion(self, sesion:Sesion) -> None:

        if self.info_pantallas_actual is None:
            self.crea_info_pantallas()
        
        self.info_pantallas_actual.add_sesion(sesion)

    
    def add_votacion(self, votacion:Votacion) -> None:

        if self.info_pantallas_actual is None:
            self.crea_info_pantallas()
        
        self.info_pantallas_actual.add_votacion(votacion)


# Instancia única (singleton simple) a usar en toda la app
info_pantallas_service = InfoPantallasService()
