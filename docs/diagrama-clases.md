# Diagrama de clases

Este diagrama resume las clases principales del backend y sus relaciones de dominio y servicio.

```mermaid
classDiagram
direction LR

class Settings {
  +concejales_file: str
  +log_dir: str
  +quorum: int
  +disposicion_bancas: dict
}

class Concejal {
  +dni: str
  +nombre: str
  +apellido: str
  +bloque: str
  +presente: bool
  +banca: int
  +mostrar_test_hasta: float
  +dispositivo_votacion: str?
  +print_corto() str
  +activar_test_temporal(duracion_s: float) None
  +to_dict() dict
}

class Banca {
  +numero_banca: int
  +nombre_concejal: str?
  +en_uso_palabra: bool
  +presente: bool
  +test_mode: bool
  +voto: ValorVoto?
  +to_dict() dict
}

class ValorVoto {
  <<enumeration>>
  POSITIVO
  NEGATIVO
  ABSTENCION
}

class Voto {
  +id: int
  +concejal: Concejal?
  +valor_voto: ValorVoto
  +hora_emision: datetime
  +to_dict() dict
}

class EstadosVotacion {
  <<enumeration>>
  APROBADA
  RECHAZADA
  EMPATADA
  EN_CURSO
  INCONCLUSA
}

class Votacion {
  +id: int
  +sesion_service: SesionService
  +estado: EstadosVotacion
  +numero: int
  +tipo: str
  +tema: str
  +computa_sobre_los_presentes: bool
  +factor_mayoria_especial: float
  +hora_inicio: datetime
  +hora_fin: datetime?
  +votos: List~Voto~
  +registrar_voto(voto: Voto) None
  +cerrar() None
  +desempatar_y_cerrar(voto_desempate: Voto) None
  +recalcular_estado_por_cambio_ausencias() None
  +contar_votos_por_tipo(tipo: ValorVoto) int
  +to_linea_votos() str
  +to_dict() dict
}

class Sesion {
  +transmision_en_vivo: bool
  +numero_sesion: int?
  +abierta: bool
  +hora_apertura_recinto: datetime
  +hora_inicio: datetime?
  +hora_fin: datetime?
  +presentes: int?
  +quorum: int?
  +disposicion_bancas: str?
  +concejales: List~Concejal~
  +votaciones: List~Votacion~
  +pedidos_uso_de_palabra: deque~Concejal~
  +en_uso_de_palabra: Concejal?
  +abrir(numero: int) None
  +cerrar() None
  +to_dict() dict
}

class InfoPantallas {
  +INTERVALO_REFRESCO_MS: int
  +sesion: Sesion
  +votacion: Votacion
  +bancas: List~Banca~
  +eventos: list~str~
  +refrescar() None
  +add_sesion(sesion: Sesion) None
  +add_votacion(votacion: Votacion) None
  +clear_votacion() None
  +to_dict() dict
}

class SesionService {
  +sesion_actual: Sesion?
  +preparar_sesion() Sesion
  +abrir_sesion(numero_sesion: int) None
  +cerrar_sesion() Sesion
  +obtener_sesion_actual() Sesion?
  +encolar_uso_palabra(concejal: Concejal) None
  +otorgar_uso_palabra() None
  +quitar_uso_palabra() None
  +cantidad_concejales_presentes() int
  +cantidad_concejales_totales() int
  +encender_indicador_transmision_en_vivo() None
  +apagar_indicador_transmision_en_vivo() None
}

class VotacionService {
  +votacion_actual: Votacion?
  +abrir_votacion(numero: int, tipo: str, tema: str, computa_sobre_los_presentes: bool, factor_mayoria_especial: float) Votacion
  +registrar_voto(voto: Voto) None
  +recalcular_cierre_por_cambio_en_presencia() None
  +cierre_forzado() Votacion
  +obtener_votacion_actual() Votacion?
  +voto_desempate(voto: Voto) Votacion
}

class InfoPantallasService {
  +info_pantallas_actual: InfoPantallas?
  +crea_info_pantallas() InfoPantallas
  +obtener_info_pantallas() InfoPantallas?
  +add_sesion(sesion: Sesion) None
  +add_votacion(votacion: Votacion) None
}

Sesion "1" *-- "0..*" Concejal : contiene
Sesion "1" *-- "0..*" Votacion : registra
Sesion "1" o-- "0..1" Concejal : en_uso_de_palabra
Sesion "1" o-- "0..*" Concejal : pedidos_uso_de_palabra

Votacion "1" *-- "0..*" Voto : agrega
Voto --> Concejal : emitido_por
Voto --> ValorVoto : valor
Votacion --> EstadosVotacion : estado
Votacion --> SesionService : consulta

Banca --> Concejal : se_construye_desde
Banca --> ValorVoto : muestra

InfoPantallas --> Sesion : refleja
InfoPantallas --> Votacion : refleja
InfoPantallas "1" *-- "0..*" Banca : renderiza

SesionService --> Sesion : administra
SesionService ..> Concejal : carga y gestiona
VotacionService --> Votacion : administra
VotacionService --> SesionService : depende_de
InfoPantallasService --> InfoPantallas : administra
InfoPantallasService --> Sesion : agrega
InfoPantallasService --> Votacion : agrega
SesionService ..> Settings : usa
```

## Alcance

El diagrama incluye:

- Clases de dominio en `app/models`
- Servicios con estado en `app/services`
- Enums relevantes para el flujo de votación

Quedaron fuera:

- Módulos funcionales sin clases, como `input_service.py` y `concejal_service.py`
- Rutas FastAPI y frontend estático

## Notas

- `SesionService`, `VotacionService` e `InfoPantallasService` se usan en la app como singletons de módulo.
- `Votacion` depende de `SesionService` para consultar la sesión abierta y recalcular cierres.
- `InfoPantallas` funciona como proyección de lectura del estado de `Sesion` y `Votacion`.
