# Arquitectura vigente de BOTONERA

Este documento describe el estado observado en la rama `v2`. No es un diseño objetivo ni autoriza refactorizaciones generales.

## 1. Vista general

```text
Teclados USB/HID
       |
       v
Servicio de captura independiente
`devices_services/teclados_fisicos/input_devices_service.py`
       |
       | POST /entradas/tecla
       v
FastAPI `app.main:app`
       |
       +-- servicios de dominio con estado en memoria
       +-- logs en disco y buffer RAM
       +-- frontends estáticos
```

El sistema está pensado para ejecutarse desde la raíz del repositorio, porque `config.json`, `data/`, `logs/` y las rutas estáticas son relativas al directorio de trabajo.

## 2. Mapa del repositorio

```text
app/
  main.py                     creación de FastAPI y montajes estáticos
  version.py                  versión expuesta por la API
  api/routes/
    moderacion.py             comandos del operador
    estados.py                endpoints de lectura
    entradas.py               recepción de teclas
  config/settings.py          carga estricta de config.json
  models/
    sesion.py                 sesión y cola de palabra
    votacion.py               estados, cálculo y cierre
    voto.py                   voto emitido
    concejal.py               datos y estado del concejal
    banca.py                  proyección visual de una banca
    InfoPantallas.py          proyección de lectura nueva
  services/
    sesion_service.py         ciclo de vida y presencia
    votacion_service.py       coordinación de votaciones
    input_service.py          traducción de teclas a acciones
    concejal_service.py       carga de CSV de concejales
    InfoPantallasService.py   singleton de la proyección nueva
  utils/logging.py            logs multinivel y cola RAM
  web/static/
    moderacion/               panel operativo
    pantalla/                 pantalla pública basada en estado_global
    pantalla2/                pantalla pública basada en info_pantallas
    monitor_simple/           visualización técnica de estado_global
    monitor_simple_pantallas/ visualización técnica de info_pantallas
    common/                   imágenes y favicon

devices_services/
  teclados_fisicos/           captura real Linux/Windows
  teclados_virtuales.py       emulador de entradas

data/concejales.csv           configuración institucional de concejales
config.json                   configuración obligatoria
requirements-backend.txt      dependencias del backend
```

## 3. Inicio de la aplicación

`app/main.py`:

1. crea `FastAPI`;
2. incluye routers de moderación, estados y entradas;
3. monta las interfaces estáticas;
4. expone `/` con estado y versión.

Los objetos `settings`, `sesion_service`, `votacion_service` e `info_pantallas_service` se crean durante la importación de módulos. No existe persistencia de estado entre reinicios.

## 4. Estado de dominio

### Sesión

`SesionService` mantiene una única referencia `sesion_actual`.

Flujo previsto:

1. `preparar_sesion()` carga concejales, quórum y disposición de bancas;
2. `abrir_sesion(numero)` habilita la sesión preparada;
3. durante la sesión se gestionan presencia, palabra y votaciones;
4. `cerrar_sesion()` fuerza el cierre de una votación en curso y elimina la referencia activa.

### Votación

`VotacionService` mantiene una única `votacion_actual`, pero la sesión conserva el historial en `sesion.votaciones`.

Reglas implementadas:

- requiere sesión abierta y quórum;
- solo una votación `EN_CURSO`;
- un voto por concejal;
- cierre automático cuando todos los presentes votaron;
- mayoría simple o factor especial;
- resultado `APROBADA`, `RECHAZADA`, `EMPATADA` o `INCONCLUSA`;
- empate pendiente de voto de desempate;
- cierre forzado registra presentes sin voto.

### Uso de la palabra

La sesión contiene:

- `pedidos_uso_de_palabra`: cola `deque`;
- `en_uso_de_palabra`: concejal actual o `None`.

La tecla correspondiente encola o retira el pedido. Moderación otorga el turno tomando el primer elemento de la cola.

## 5. Entrada de teclados

El servicio físico identifica cada dispositivo y envía un identificador lógico, por ejemplo `dev01`.

El backend busca el concejal cuyo `dispositivo_votacion` coincide y aplica el mapa actual de `input_service.py`:

- `1`: voto positivo;
- `2`: abstención;
- `3`: voto negativo;
- `7`: solicitar o retirar uso de la palabra; si el concejal está hablando, finalizar su turno;
- `8`: activar test visual temporal;
- `9`: alternar presencia.

Cualquier cambio en este mapa requiere revisar el servicio físico, el emulador, el manual y las pantallas.

## 6. APIs

### Entrada

- `POST /entradas/tecla`

### Moderación

- `POST /moderacion/preparar_sesion`
- `POST /moderacion/abrir_sesion`
- `POST /moderacion/cerrar_sesion`
- `POST /moderacion/abrir_votacion`
- `POST /moderacion/cerrar_votacion`
- `POST /moderacion/voto_desempate`
- `POST /moderacion/otorgar_uso_palabra`
- `POST /moderacion/quitar_uso_palabra`
- `POST /moderacion/indicador_transmision_on`
- `POST /moderacion/indicador_transmision_off`

### Lectura

- `GET /estados/estado_global`
- `GET /estados/info_pantallas`
- `GET /estados/configuracion`

## 7. Dos modelos de lectura para pantallas

### `estado_global`

Devuelve:

```json
{
  "hay_sesion": true,
  "sesion": {},
  "eventos": []
}
```

Es consumido por moderación, pantalla existente y monitor simple. La sesión serializada incluye concejales, votaciones, cola de palabra y otros campos.

### `info_pantallas`

Es una proyección específica que intenta desacoplar las pantallas del objeto completo de sesión. `pantalla2` la combina con `/estados/configuracion` para obtener la disposición de bancas.

Esta migración no está finalizada. Los dos contratos deben mantenerse hasta una decisión explícita.

## 8. Frontends

Los frontends no persisten estado de negocio. Renderizan el último JSON recibido mediante polling.

### Moderación

Cuatro cuadrantes:

- Q1: comandos de sesión y votación;
- Q2: orden del día desde CSV local;
- Q3: plano del recinto y uso de la palabra;
- Q4: eventos filtrados por nivel.

Existe un bus JavaScript interno para desacoplar los cuadrantes. El polling usa `/estados/estado_global` cada 250 ms.

### Pantalla

`/pantalla` consume `/estados/estado_global` cada 300 ms. Presenta estado de sesión, quórum, votación, recinto, palabra y eventos.

### Pantalla 2

`/pantalla2` consume `/estados/info_pantallas` y `/estados/configuracion` cada 300 ms. Es la nueva línea de refactorización de la pantalla pública.

## 9. Logging

`log_internal(tag, level, message)` escribe:

- nivel 1 en archivo 1;
- nivel 2 en archivos 1 y 2;
- nivel 3 en archivos 1, 2 y 3.

También agrega cada evento a un `deque` de 20 elementos con secuencia incremental. `estado_global` entrega ese buffer al frontend.

## 10. Límites arquitectónicos actuales

- El estado es local al proceso.
- No hay base de datos ni recuperación tras reinicio.
- No hay suite automatizada de pruebas.
- Los contratos frontend/backend se validan principalmente por integración manual.
- Las rutas y archivos relativos dependen del directorio desde el cual se inicia el proceso.

Consultar `KNOWN_ISSUES.md` antes de proponer soluciones sobre estos límites.
