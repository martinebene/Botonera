# Instrucciones para agentes

Este archivo es la fuente canónica de instrucciones para cualquier agente de desarrollo que trabaje en este repositorio.

## 1. Contexto y ramas

- `main` contiene el sistema actualmente desplegado en producción en el Concejo Deliberante de Puerto Madryn.
- `v2` contiene la refactorización y las funcionalidades en desarrollo.
- Nunca modificar `main` directamente.
- Para una tarea nueva, crear una rama corta desde `v2` y abrir una Pull Request hacia `v2`, salvo instrucción explícita en contrario.
- No hacer merge, despliegue, cambios de infraestructura ni modificaciones de servicios de producción sin autorización explícita.

Antes de editar, verificar siempre:

```bash
git status
git branch --show-current
git log -1 --oneline
```

Si la rama actual es `main`, detenerse.

## 2. Orden de lectura obligatorio

1. Este archivo.
2. `README.md`.
3. `docs/agents/ARCHITECTURE.md`.
4. `docs/agents/KNOWN_ISSUES.md`.
5. Solo los archivos propietarios del comportamiento que se va a modificar.
6. `docs/agents/DEVELOPMENT.md` antes de validar o entregar cambios.

No recorrer ni modificar archivos irrelevantes para la tarea. Los registros históricos de `logs/`, imágenes, ZIP y PDF no son contexto de implementación salvo que la tarea los mencione expresamente.

## 3. Objetivo del sistema

BOTONERA gestiona sesiones legislativas, presencia, quórum, votaciones electrónicas, uso de la palabra, pantallas públicas y eventos operativos. El backend FastAPI recibe pulsaciones de dispositivos físicos mediante un servicio separado y expone estado a frontends estáticos que consultan periódicamente la API.

Es un sistema institucional en uso real. La continuidad operativa y la compatibilidad pesan más que una refactorización estética.

## 4. Arquitectura vigente que debe preservarse

- Backend: FastAPI en `app/`.
- Estado de dominio en memoria mediante instancias globales de servicios:
  - `sesion_service`
  - `votacion_service`
  - `info_pantallas_service`
- Entrada física desacoplada en `devices_services/teclados_fisicos/`.
- Frontends HTML, CSS y JavaScript sin framework en `app/web/static/`.
- Configuración obligatoria cargada desde `config.json` al importar la aplicación.
- Logs en disco y buffer circular en memoria mediante `app/utils/logging.py`.

No reemplazar esta arquitectura, incorporar base de datos, WebSocket, framework frontend, contenedor, cola, autenticación o nueva infraestructura como efecto lateral de otra tarea. Esas decisiones requieren alcance propio.

## 5. Contratos críticos

### API de entrada

`POST /entradas/tecla`

```json
{
  "dispositivo": "dev01",
  "tecla": "1"
}
```

El servicio de teclados solo captura, identifica y transmite. La lógica de negocio pertenece al backend.

### APIs de moderación

Las acciones operativas viven bajo `/moderacion`, entre ellas:

- `preparar_sesion`
- `abrir_sesion`
- `cerrar_sesion`
- `abrir_votacion`
- `cerrar_votacion`
- `voto_desempate`
- `otorgar_uso_palabra`
- `quitar_uso_palabra`
- indicadores de transmisión

No cambiar rutas, cuerpos JSON, nombres de campos, tipos o respuestas sin rastrear todos sus consumidores.

### APIs de lectura

- `/estados/estado_global`: estado completo consumido por moderación, monitor y pantalla existente.
- `/estados/info_pantallas`: proyección nueva consumida por `pantalla2`.
- `/estados/configuracion`: configuración fija para frontends.

`/pantalla` y `/pantalla2` representan una migración en curso. No eliminar, fusionar ni renombrar una por parecer duplicada.

### Frontend

- El polling actual es parte del contrato operativo: aproximadamente 250–300 ms.
- Los identificadores HTML, formas del JSON, rutas estáticas y nombres de clases usadas desde JavaScript son contratos internos.
- Las áreas con scroll interno y las alturas de los cuadrantes fueron diseñadas para evitar que un panel deforme el resto.
- Cambios en un cuadrante no deben alterar visual ni funcionalmente los demás salvo requerimiento explícito.

## 6. Reglas de implementación

1. Resolver la causa concreta con el cambio mínimo coherente.
2. No hacer limpieza general, renombrados masivos, formateo global ni reordenamiento de imports fuera del alcance.
3. No corregir silenciosamente comportamientos dudosos encontrados durante otra tarea. Registrarlos en la entrega o en un issue.
4. Mantener español en textos de interfaz, mensajes de dominio y documentación existente.
5. Para Python, usar `snake_case` en funciones y variables, `PascalCase` en clases y nombres explícitos.
6. No introducir secretos, datos personales reales, tokens, rutas locales del desarrollador ni archivos generados.
7. No editar `data/concejales.csv`, `config.json`, órdenes del día, imágenes de bancas o mapeos físicos con datos reales salvo que la tarea lo exija.
8. No agregar dependencias sin justificar necesidad, compatibilidad Linux/Windows y efecto en producción.
9. No asumir que una mejora técnica es compatible con múltiples procesos: el estado actual es local al proceso.
10. Toda modificación de reglas de votación, quórum, presencia, desempate o cierre requiere casos explícitos y validación del flujo completo.

## 7. Propiedad por área

- Inicio, rutas y montajes: `app/main.py`, `app/api/routes/`.
- Configuración: `app/config/settings.py`, `config.json`.
- Entidades y serialización: `app/models/`.
- Reglas de sesión: `app/services/sesion_service.py`.
- Reglas de votación: `app/services/votacion_service.py`, `app/models/votacion.py`.
- Traducción de teclas y entrada de negocio: `app/services/input_service.py`.
- Proyección nueva de pantallas: `app/models/InfoPantallas.py`, `app/services/InfoPantallasService.py`.
- Logging: `app/utils/logging.py`.
- Moderación: `app/web/static/moderacion/`.
- Pantalla vigente: `app/web/static/pantalla/`.
- Pantalla nueva en migración: `app/web/static/pantalla2/`.
- Captura de dispositivos: `devices_services/teclados_fisicos/`.

Antes de cambiar un contrato, buscar referencias en todas estas áreas.

## 8. Validación mínima obligatoria

No existe todavía una suite automatizada suficiente. Cada entrega debe indicar exactamente qué se ejecutó.

Como mínimo:

```bash
python -m compileall app devices_services
python -m uvicorn app.main:app --reload
```

Luego verificar los endpoints y recorridos afectados según `docs/agents/DEVELOPMENT.md`.

Para cambios frontend:

- abrir la pantalla afectada en navegador;
- observar varias iteraciones de polling;
- probar sin sesión, recinto preparado, sesión abierta, votación en curso y cierre si corresponde;
- comprobar consola del navegador y respuesta HTTP;
- confirmar que no se alteraron otros cuadrantes o pantallas.

Para cambios de dominio:

- probar caso válido;
- probar rechazo esperado;
- probar cambio de presencia;
- probar cierre automático y forzado cuando aplique;
- comprobar logs y JSON de estado.

`compileall` no demuestra que el sistema funcione. No presentar una tarea como validada solo por compilar.

## 9. Entrega esperada del agente

Toda entrega debe incluir:

- objetivo realizado;
- archivos modificados;
- comportamiento anterior y nuevo;
- contratos afectados o preservados;
- validaciones ejecutadas y resultado;
- riesgos, supuestos y aspectos no verificados;
- pasos manuales necesarios, si existen.

No ocultar incertidumbre. Si una regla de negocio no está definida en el repositorio o en la tarea, no inventarla.

## 10. Estado conocido del repositorio

Hay documentación y comportamiento en transición, archivos históricos y ausencia de pruebas automáticas. Las observaciones vigentes están registradas en `docs/agents/KNOWN_ISSUES.md`. Esas observaciones no autorizan a corregirlas dentro de una tarea no relacionada.
