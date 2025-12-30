from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Tuple

from app.services.sesion_service import sesion_service
from app.models.votacion import Votacion
from app.models.voto import Voto
from app.models.concejal import Concejal
from app.config import settings


def _write_log(linea: str) -> None:
    """Escribe una línea en el archivo de log."""
    with open(settings.log_file, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _log_votacion_apertura_ok(votacion: Votacion, numero_sesion: int) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hi = votacion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")
    linea = (
        f"[{ts}] VOTACION_APERTURA_OK; "
        f"numero_sesion={numero_sesion}; "
        f"numero_votacion={votacion.numero}; "
        f"tipo={votacion.tipo}; "
        f"tema={votacion.tema}; "
        f"hora_inicio={hi}"
    )
    _write_log(linea)


def _log_votacion_apertura_fallida(
    numero_sesion: Optional[int],
    numero_votacion: int,
    motivo: str,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sesion_str = str(numero_sesion) if numero_sesion is not None else "N/A"
    linea = (
        f"[{ts}] VOTACION_APERTURA_FALLIDA; "
        f"numero_sesion={sesion_str}; "
        f"numero_votacion={numero_votacion}; "
        f"motivo={motivo}"
    )
    _write_log(linea)


def _log_voto_recibido(
    votacion: Votacion,
    voto: Voto,
    numero_sesion: int,
    auto_cierre: bool,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    concejal_info = f"{voto.concejal.apellido}, {voto.concejal.nombre} (dni={voto.concejal.dni})"
    auto_str = "SI" if auto_cierre else "NO"
    linea = (
        f"[{ts}] VOTO_RECIBIDO_OK; "
        f"numero_sesion={numero_sesion}; "
        f"numero_votacion={votacion.numero}; "
        f"concejal={concejal_info}; "
        f"valor_voto={voto.valor_voto}; "
        f"auto_cierre={auto_str}"
    )
    _write_log(linea)


def _log_votacion_cierre_ok(
    votacion: Votacion,
    numero_sesion: int,
    cierre_forzado: bool,
    concejales_sin_voto: Optional[List[Concejal]] = None,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hi = votacion.hora_inicio.strftime("%Y-%m-%d %H:%M:%S")
    hf = votacion.hora_fin.strftime("%Y-%m-%d %H:%M:%S") if votacion.hora_fin else "N/A"
    tipo_cierre = "FORZADO" if cierre_forzado else "AUTOMATICO"

    linea = (
        f"[{ts}] VOTACION_CIERRE_{tipo_cierre}; "
        f"numero_sesion={numero_sesion}; "
        f"numero_votacion={votacion.numero}; "
        f"hora_inicio={hi}; "
        f"hora_fin={hf}"
    )
    _write_log(linea)

    if cierre_forzado and concejales_sin_voto:
        for c in concejales_sin_voto:
            info_c = f"{c.apellido}, {c.nombre} (dni={c.dni})"
            linea_no_voto = (
                f"[{ts}] VOTACION_CIERRE_FORZADO_NO_VOTO; "
                f"numero_sesion={numero_sesion}; "
                f"numero_votacion={votacion.numero}; "
                f"concejal={info_c}"
            )
            _write_log(linea_no_voto)


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

    def _calcular_auto_cierre(self, sesion, votacion) -> bool:
        """
        Devuelve True si, con el estado ACTUAL de presentes y votos,
        corresponde cerrar automáticamente la votación.

        Regla: todos los concejales presentes ya votaron.
        """
        presentes = [c for c in sesion.concejales if c.presente]
        dnis_presentes = {c.dni for c in presentes}
        dnis_que_votaron = {v.concejal.dni for v in votacion.votos}

        return dnis_presentes.issubset(dnis_que_votaron)

    def _cerrar_automaticamente(self, sesion, votacion) -> None:
        """
        Ejecuta el cierre automático de la votación:
        - marca hora_fin
        - loguea cierre automático
        - borra votacion_actual
        """
        votacion.cerrar()
        _log_votacion_cierre_ok(
            votacion=votacion,
            numero_sesion=sesion.numero_sesion,
            cierre_forzado=False,
            concejales_sin_voto=None,
        )
        self.votacion_actual = None

    # ------------------------------------------------------------------
    # API pública del servicio
    # ------------------------------------------------------------------

    def abrir_votacion(self, numero: int, tipo: str, tema: str) -> Votacion:
        """
        Abre una nueva votación en la sesión actual.
        """

        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            _log_votacion_apertura_fallida(
                numero_sesion=None,
                numero_votacion=numero,
                motivo="no_hay_sesion_abierta",
            )
            raise ValueError("No hay sesión abierta. No se puede abrir una votación.")

        if self.votacion_actual is not None and self.votacion_actual.abierta:
            _log_votacion_apertura_fallida(
                numero_sesion=sesion.numero_sesion,
                numero_votacion=numero,
                motivo="ya_hay_votacion_abierta",
            )
            raise ValueError("Ya hay una votación abierta. Debe cerrarla antes de abrir otra.")

        votacion = Votacion(numero=numero, tipo=tipo, tema=tema)
        sesion.votaciones.append(votacion)
        self.votacion_actual = votacion

        _log_votacion_apertura_ok(votacion, sesion.numero_sesion)

        return votacion

    def registrar_voto(self, voto: Voto) -> Tuple[Votacion, bool]:
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
            raise ValueError("no_hay_sesion_abierta")

        if self.votacion_actual is None or not self.votacion_actual.abierta:
            raise ValueError("no_hay_votacion_abierta")

        votacion = self.votacion_actual

        # Puede levantar ValueError("votacion_cerrada" o "concejal_ya_voto")
        votacion.registrar_voto(voto)

        # 1) calcular si corresponde cierre automático
        auto_cierre = self._calcular_auto_cierre(sesion, votacion)

        # 2) loguear SIEMPRE el voto recibido con info del auto_cierre
        _log_voto_recibido(votacion, voto, sesion.numero_sesion, auto_cierre)

        # 3) si corresponde, cerrar y loguear el cierre automático
        if auto_cierre:
            self._cerrar_automaticamente(sesion, votacion)

        return votacion, auto_cierre

    def recalcular_cierre_por_cambio_en_presencia(self) -> Tuple[Optional[Votacion], bool]:
        """
        Se llama cuando cambia el estado presente/ausente de algún concejal
        (por ejemplo, con la tecla 7).

        Si, después de ese cambio, el conjunto de concejales presentes queda
        contenido en los que ya votaron, se cierra la votación automáticamente.

        Devuelve: (votacion_resultante, auto_cerrada: bool)
        """

        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            return None, False

        if self.votacion_actual is None or not self.votacion_actual.abierta:
            return self.votacion_actual, False

        votacion = self.votacion_actual

        auto_cierre = self._calcular_auto_cierre(sesion, votacion)

        if not auto_cierre:
            return votacion, False

        # Cerrar y loguear cierre automático reutilizando el mismo helper
        self._cerrar_automaticamente(sesion, votacion)
        return votacion, True

    def cierre_forzado(self) -> Votacion:
        """
        Fuerza el cierre de la votación actual.
        """

        sesion = sesion_service.obtener_sesion_actual()
        if sesion is None or not sesion.abierta:
            raise ValueError("No hay sesión abierta.")

        if self.votacion_actual is None or not self.votacion_actual.abierta:
            raise ValueError("No hay votación abierta.")

        votacion = self.votacion_actual

        presentes = [c for c in sesion.concejales if c.presente]
        dnis_que_votaron = {v.concejal.dni for v in votacion.votos}
        concejales_sin_voto = [c for c in presentes if c.dni not in dnis_que_votaron]

        votacion.cerrar()

        _log_votacion_cierre_ok(
            votacion=votacion,
            numero_sesion=sesion.numero_sesion,
            cierre_forzado=True,
            concejales_sin_voto=concejales_sin_voto,
        )

        self.votacion_actual = None

        return votacion

    def obtener_votacion_actual(self) -> Optional[Votacion]:
        return self.votacion_actual


# Instancia única del servicio a importar desde otras partes
votacion_service = VotacionService()
