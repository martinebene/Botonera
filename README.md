# 🏛 BOTONERA

## Sistema Integral de Gestión de Sesiones y Votación Electrónica

Sistema para la gestión de sesiones del Concejo Deliberante,
incluyendo votación electrónica, uso de la palabra y visualización en
tiempo real del estado de la sesion.

------------------------------------------------------------------------

# 📌 Descripción General

Es una solución compuesta por:

-   🧠 Backend en **FastAPI**
-   ⌨ Servicio independiente de captura de teclados físicos (Ver readme interno)
-   🖥 Frontends estáticos (Moderación, Pantalla Recinto, Monitor
    Técnico)
-   🔁 Servicios gestionados por systemd
-   🌐 Exposición LAN vía Nginx
-   📊 Sistema de logs multinivel + buffer RAM para frontend

Diseñado para entornos Linux (Debian / Ubuntu / Mint).

------------------------------------------------------------------------

# 🏗 Arquitectura

    [Nginx :80]
            ↓
    [Gunicorn + UvicornWorker]
            ↓
    [FastAPI app.main:app]
            |
            ├── /monitor-simple
            ├── /moderacion
            ├── /pantalla
            ├── /bancas/*.png
            ├── /estados/*
            └── /entradas/tecla

Servicio paralelo:

    [Servicio teclados físicos]
            ↓
    POST → /entradas/tecla

Comunicación interna por `127.0.0.1`.

------------------------------------------------------------------------

# 📁 Estructura del Proyecto

    BOTONERA/
    │
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   ├── models/
    │   ├── services/
    │   ├── utils/
    │   └── web/static/
    │
    ├── devices_services/
    │   └── teclados_fisicos/
    │
    ├── data/
    ├── logs/
    ├── config.json
    └── venv/

------------------------------------------------------------------------
# 🖥 Frontends

El sistema incluye **tres interfaces independientes**, todas
desacopladas del backend en términos de estado interno.

## 1️⃣ Moderación (`/moderacion`)

Pantalla operativa utilizada por el presidente / secretario.

Responsabilidades:

-   Abrir / cerrar sesión
-   Abrir / cerrar votaciones
-   Configurar tipo, mayoría especial y cómputo
-   Gestión de desempate
-   Visualización de quórum en tiempo real
-   Carga de orden del día vía CSV
-   Consola de eventos con filtrado por nivel

Características técnicas:

-   Layout en grid 2x2
-   Polling cada 250--300 ms a `/estados/estado_global`
-   Sin estado complejo interno (renderiza según último JSON recibido)
-   Sistema de bus interno para desacoplar cuadrantes
-   Validación estricta de CSV (RFC4180 compatible)

## 2️⃣ Pantalla Recinto (`/pantalla`)

Pantalla pública proyectada en sala.

Responsabilidades:

-   Visualización del estado de la votación
-   Render dinámico del recinto según `disposicion_bancas`
-   Render de bancas con imágenes individuales
-   Atenuación visual según presencia / uso de la palabra
-   Lista scrolleable FIFO de uso de la palabra
-   Consola lateral de eventos principales

Características técnicas:

-   Layout optimizado sin scroll global
-   Render dinámico del plano del recinto
-   Separación clara entre canvas recinto y lista lateral
-   Diseño de alta legibilidad para proyección

## 3️⃣ Monitor Técnico (`/monitor-simple`)

Pantalla minimalista orientada a verificación técnica.

Responsabilidades:

-   Mostrar JSON crudo del estado global
-   Diagnóstico rápido de conectividad
-   Verificación de estructura del backend

## 🔄 Modelo de Actualización

Todos los frontends:

-   Utilizan polling periódico al endpoint `/estados/estado_global`
-   No almacenan estado persistente
-   Son tolerantes a errores HTTP
-   Indican estado de conexión visualmente
-   Pueden recargarse sin afectar backend

## 🧠 Principios de Diseño Frontend

-   Cuadrantes desacoplados
-   Sin dependencia circular entre vistas
-   Render puro basado en estado recibido
-   Layout que evita que el contenido altere alturas globales
-   Scroll interno únicamente en áreas específicas
-   CSS modular por panel

------------------------------------------------------------------------
# ⚙ Configuración

Archivo `config.json`:

``` json
{
  "concejales_file": "data/concejales.csv",
  "log_dir": "logs/",
  "quorum": 7,
  "disposicion_bancas": {
    "filas": [
      { "fila": 3, "columnas": 5 },
      { "fila": 2, "columnas": 4 },
      { "fila": 1, "columnas": 3 }
    ]
  }
}
```
------------------------------------------------------------------------

# 🚀 Instalación en Producción (Resumen)
-   Ver documentacion especifica

------------------------------------------------------------------------

# 📊 Logging

Sistema de logs multinivel por fecha:

-   Nivel 1 → detalle completo
-   Nivel 2 → intermedio
-   Nivel 3 → eventos principales

Además incluye buffer circular en RAM para visualización en frontend.

------------------------------------------------------------------------

# 🧠 Reglas de Dominio

-   Solo una sesión activa a la vez
-   Solo una votación activa por sesión
-   Cierre automático cuando votan todos los presentes
-   Soporte mayoría simple y especial
-   Gestión FIFO de uso de la palabra
-   Control dinámico de quórum

------------------------------------------------------------------------

# 🛡 Buenas Prácticas Aplicadas

-   Separación backend / hardware
-   Proxy reverso
-   Reinicio automático systemd
-   Logs estructurados
-   Comunicación interna por loopback
-   Frontends desacoplados del estado interno

------------------------------------------------------------------------

# 📄 Licencia

Proyecto institucional privado.
