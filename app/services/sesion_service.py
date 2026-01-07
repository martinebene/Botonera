from typing import Optional, List
from datetime import datetime

from app.models.sesion import Sesion
from app.models.concejal import Concejal
from app.services.concejal_service import cargar_concejales_desde_archivo
from app.config import settings
from app.utils import logging


def _log_sesion_apertura_ok(sesion: Sesion) -> None:
    """
    Loguea una apertura de sesión exitosa.
    Formato:
    [fecha hora] SESION_APERTURA_OK; numero_sesion=X; hora_inicio=YYYY-MM-DD HH:MM:SS
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hora_inicio_str = sesion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")
    linea = (
        f"[{timestamp}] SESION_APERTURA_OK; "
        f"numero_sesion={sesion.numero_sesion}; "
        f"hora_inicio={hora_inicio_str}"
    )
    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _log_sesion_apertura_fallida(numero_sesion: int, motivo: str) -> None:
    """
    Loguea un intento de apertura de sesión que fue rechazado.
    Formato:
    [fecha hora] SESION_APERTURA_FALLIDA; numero_sesion=X; motivo=...
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = (
        f"[{timestamp}] SESION_APERTURA_FALLIDA; "
        f"numero_sesion={numero_sesion}; "
        f"motivo={motivo}"
    )
    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _log_sesion_cierre_ok(sesion: Sesion) -> None:
    """
    Loguea un cierre de sesión exitoso.
    Formato:
    [fecha hora] SESION_CIERRE_OK; numero_sesion=X; hora_inicio=...; hora_fin=...
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hora_inicio_str = sesion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")
    hora_fin_str = sesion.hora_fin.strftime("%Y-%m-%d %H:%M:%S") if sesion.hora_fin else "N/A"
    linea = (
        f"[{timestamp}] SESION_CIERRE_OK; "
        f"numero_sesion={sesion.numero_sesion}; "
        f"hora_inicio={hora_inicio_str}; "
        f"hora_fin={hora_fin_str}"
    )
    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _log_sesion_cierre_fallida(motivo: str) -> None:
    """
    Loguea un intento de cierre de sesión rechazado.
    Formato:
    [fecha hora] SESION_CIERRE_FALLIDA; motivo=...
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = (
        f"[{timestamp}] SESION_CIERRE_FALLIDA; "
        f"motivo={motivo}"
    )
    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


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
            motivo = "ya_hay_sesion_abierta"
            _log_sesion_apertura_fallida(numero_sesion, motivo)
            logging.log_internal("SESION",1, "Rechazo de apertura de sesion porque ya hay sesion abierta")
            raise ValueError("Ya hay una sesión abierta. Debe cerrarla antes de abrir otra.")

        # Cargamos concejales ANTES de crear la sesión
        try:
            concejales: List[Concejal] = cargar_concejales_desde_archivo(settings.concejales_file)
        except FileNotFoundError:
            motivo = "archivo_concejales_no_encontrado"
            _log_sesion_apertura_fallida(numero_sesion, motivo)
            logging.log_internal("SESION",1, "Rechazo de apertura de sesion porque no hay archivo de concejales")
            raise ValueError("No se encontró el archivo de concejales. No se puede abrir la sesión.")

        if not concejales:
            motivo = "lista_concejales_vacia"
            logging.log_internal("SESION",1, "Rechazo de apertura de sesion porque no hay concejales en el archivo")
            _log_sesion_apertura_fallida(numero_sesion, motivo)
            raise ValueError("La lista de concejales está vacía. No se puede abrir la sesión.")

        # Si todo está bien, creamos la sesión
        sesion = Sesion(numero_sesion=numero_sesion)
        sesion.concejales = concejales

        self.sesion_actual = sesion

        # Log de apertura exitosa
        _log_sesion_apertura_ok(sesion)
        logging.log_internal("SESION",1, "Apertura de sesion")
        return sesion

    def cerrar_sesion(self) -> Sesion:
        """
        Cierra la sesión actual.

        Reglas:
        - Si no hay sesión -> ValueError + log de CIERRE_FALLIDA.
        - Si ya está cerrada -> ValueError + log de CIERRE_FALLIDA.
        - Si se cierra correctamente -> log de CIERRE_OK.
        """

        if self.sesion_actual is None:
            motivo = "no_hay_sesion_abierta"
            logging.log_internal("SESION",1, "Cierre de sesion fallido porque no hay sesion abierta")
            _log_sesion_cierre_fallida(motivo)
            raise ValueError("No hay ninguna sesión abierta.")

        sesion = self.sesion_actual

        if not sesion.abierta:
            motivo = "sesion_ya_cerrada"
            logging.log_internal("SESION",1, "Cierre de sesion fallido porque no hay sesion abierta")
            _log_sesion_cierre_fallida(motivo)
            raise ValueError("La sesión ya está cerrada.")

        # Cerramos la sesión (esto setea hora_fin y abierta=False)
        sesion.cerrar()

        # Log de cierre exitoso
        logging.log_internal("SESION",1, "Cierre de sesion")
        _log_sesion_cierre_ok(sesion)

        # Dejamos la referencia en None (si preferís, podríamos dejar la Sesion cerrada)
        self.sesion_actual = None

        return sesion

    def obtener_sesion_actual(self) -> Optional[Sesion]:
        """Devuelve la sesión actual (o None si no hay)."""
        return self.sesion_actual


    def encolar_uso_palabra(self, concejal: Concejal) -> None:
        """Encola o Desencola un concejal"""
        if concejal not in self.sesion_actual.pedidos_uso_de_palabra:
            self.sesion_actual.pedidos_uso_de_palabra.append(concejal)
            logging.log_internal("PALABRA",1, concejal.print_corto() + " pidio la palabra")
        else:
            self.sesion_actual.pedidos_uso_de_palabra.remove(concejal)
            logging.log_internal("PALABRA",1, concejal.print_corto() + " retiro el pedido la palabra")

    def otorgar_uso_palabra(self) -> None:
        if self.sesion_actual.pedidos_uso_de_palabra:
            self.sesion_actual.en_uso_de_palabra=self.sesion_actual.pedidos_uso_de_palabra.popleft()
        else:
            self.sesion_actual.en_uso_de_palabra=None

    def quitar_uso_palabra(self) -> None:
            self.sesion_actual.en_uso_de_palabra=None

# Instancia única (singleton simple) a usar en toda la app
sesion_service = SesionService()
