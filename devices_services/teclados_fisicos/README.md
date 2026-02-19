# ⌨ BOTONERA -- Servicio de Teclados Físicos

## Agente de Captura y Envío de Pulsaciones al Backend

Servicio independiente encargado de:

-   Detectar dispositivos de entrada físicos (teclados numéricos USB /
    HID)
-   Identificar cada dispositivo de manera única (fingerprint)
-   Traducir teclas físicas a comandos lógicos
-   Enviar eventos al backend FastAPI vía HTTP POST
-   Permitir mapeo interactivo de dispositivos
-   Ejecutarse como servicio systemd en producción

------------------------------------------------------------------------

# 🎯 Objetivo

Desacoplar completamente la lógica de hardware del backend.

El backend **no accede directamente a dispositivos físicos**. Este
servicio actúa como puente entre hardware y API.

------------------------------------------------------------------------

# 🏗 Arquitectura

    [Teclado físico USB]
            ↓
    [input_devices_service.py]
            ↓
    POST http://127.0.0.1:8000/entradas/tecla
            ↓
    [Backend FastAPI]

Comunicación exclusivamente por loopback (127.0.0.1).

------------------------------------------------------------------------

# 📁 Ubicación en el Proyecto

    BOTONERA/
    └── devices_services/
        └── teclados_fisicos/
            ├── input_devices_service.py
            ├── requirements.txt
            ├── data/
            │   └── mapeo_teclados.json
            └── venv/

------------------------------------------------------------------------

# 🖥 Compatibilidad de Sistema Operativo

## Linux

-   Basado en `evdev`
-   Requiere pertenecer al grupo `input`
-   Permite lectura directa de `/dev/input/event*`

## Windows

-   Basado en Raw Input (ctypes)
-   Identificación por device path único
-   Permite múltiples teclados simultáneos

------------------------------------------------------------------------

# 🔐 Permisos Requeridos (Linux)

Agregar usuario del servicio al grupo `input`:

    sudo usermod -aG input botonera

Reiniciar sistema.

------------------------------------------------------------------------

# ⚙ Variables de Entorno

El servicio utiliza:

    API_BASE_URL=http://127.0.0.1:8000

Configurada en systemd.

------------------------------------------------------------------------

# 🔄 Formato del POST

Endpoint:

    POST /entradas/tecla

Body JSON:

``` json
{
  "dispositivo": "dev01",
  "tecla": "1"
}
```

------------------------------------------------------------------------

# 🗺 Sistema de Mapeo

Archivo:

    data/mapeo_teclados.json

Permite:

-   Asociar fingerprint físico → identificador lógico (dev01, dev02,
    etc.)
-   Evitar reasignaciones accidentales
-   Reconfigurar dispositivos sin modificar backend

------------------------------------------------------------------------

# 🛠 Modo Interactivo

Comando:

    teclados-menu

Funcionalidades:

1.  Crear nuevo mapeo
2.  Debug de entradas en tiempo real
3.  Verificar dispositivos detectados

El servicio systemd se detiene automáticamente mientras el menú está
activo.

------------------------------------------------------------------------

# 📜 Logs

El servicio escribe en:

    journalctl -u botonera-teclados -f

También disponible mediante:

    teclados-log

------------------------------------------------------------------------

# 🔁 Servicio systemd

Archivo:

    /etc/systemd/system/botonera-teclados.service

ExecStart:

    python input_devices_service.py

Características:

-   Reinicio automático
-   Dependencia del backend
-   Ejecución como usuario no-root
-   Output redirigido a journal

------------------------------------------------------------------------

# 🛡 Buenas Prácticas Implementadas

-   Separación total hardware/backend
-   Comunicación local segura
-   Soporte multiplataforma
-   Identificación persistente de dispositivos
-   Mapeo configurable sin recompilar
-   Servicio aislado y reiniciable

------------------------------------------------------------------------

# 🧪 Modo Desarrollo

Ejecutar manualmente:

    python input_devices_service.py

Debe estar detenido el servicio systemd para evitar doble captura.

------------------------------------------------------------------------

# 📌 Consideraciones Técnicas

-   El servicio no contiene lógica de negocio.
-   No valida votos ni reglas de sesión.
-   Solo transmite eventos físicos.
-   Backend es responsable de validaciones.

------------------------------------------------------------------------

# 📄 Licencia

Uso institucional interno.
