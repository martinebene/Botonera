# Desarrollo y validación

## 1. Requisitos

- Python compatible con las dependencias fijadas en `requirements-backend.txt`.
- Navegador moderno.
- Para teclados físicos en Linux: acceso a dispositivos de entrada y paquete `evdev`.
- Ejecutar los comandos desde la raíz del repositorio.

## 2. Preparación del backend

### Windows PowerShell

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-backend.txt
python -m uvicorn app.main:app --reload
```

### Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-backend.txt
python -m uvicorn app.main:app --reload
```

La aplicación queda normalmente en `http://127.0.0.1:8000`.

## 3. Verificación inicial

Comprobar:

```text
GET /
GET /estados/configuracion
GET /estados/estado_global
GET /estados/info_pantallas
```

Abrir:

```text
/moderacion
/pantalla
/pantalla2
/monitor-simple
/monitor-simple-pantallas
/docs
```

No asumir que una respuesta HTTP 200 implica que el recorrido funcional es correcto.

## 4. Flujo manual básico

Las llamadas siguientes son orientativas. Usar Swagger en `/docs`, `curl`, PowerShell o un cliente HTTP.

### 4.1 Preparar recinto

```http
POST /moderacion/preparar_sesion
```

Debe cargar `data/concejales.csv`, el quórum y la disposición de bancas.

### 4.2 Abrir sesión

```http
POST /moderacion/abrir_sesion
Content-Type: application/json

{
  "numero_sesion": 1
}
```

### 4.3 Marcar presencia

```http
POST /entradas/tecla
Content-Type: application/json

{
  "dispositivo": "dev01",
  "tecla": "9"
}
```

Repetir con dispositivos válidos hasta alcanzar quórum.

### 4.4 Abrir votación

```http
POST /moderacion/abrir_votacion
Content-Type: application/json

{
  "numero": 1,
  "tipo": "Otro",
  "tema": "Prueba local",
  "computa_sobre_los_presentes": true,
  "factor_mayoria_especial": 0
}
```

### 4.5 Emitir votos

```http
POST /entradas/tecla
Content-Type: application/json

{
  "dispositivo": "dev01",
  "tecla": "1"
}
```

Mapa vigente:

- `1`: positivo;
- `2`: abstención;
- `3`: negativo;
- `7`: palabra;
- `8`: test visual;
- `9`: presencia.

### 4.6 Cierre y desempate

Probar según el cambio:

```text
POST /moderacion/cerrar_votacion
POST /moderacion/voto_desempate
POST /moderacion/cerrar_sesion
```

## 5. Servicio de teclados físicos

Usa un entorno separado porque tiene dependencias específicas:

```bash
cd devices_services/teclados_fisicos
python -m venv venv
# activar el entorno
python -m pip install -r requirements.txt
python input_devices_service.py
```

En producción el servicio usa `API_BASE_URL`, normalmente `http://127.0.0.1:8000`.

No ejecutar simultáneamente el servicio real y otra instancia que capture los mismos dispositivos.

## 6. Validación estática mínima

```bash
python -m compileall app devices_services
```

Cuando se agreguen herramientas de lint o pruebas, documentarlas aquí y fijarlas en dependencias. No declarar comandos inexistentes.

## 7. Matriz mínima por tipo de cambio

### Backend de rutas o serialización

- respuesta válida;
- error esperado con HTTP correcto;
- forma exacta del JSON;
- compatibilidad con todos los frontends consumidores;
- Swagger sin errores de esquema.

### Sesión, presencia o palabra

- sin recinto preparado;
- recinto preparado y sesión cerrada;
- sesión abierta;
- concejal ausente y presente;
- cola vacía, un pedido y varios pedidos;
- cierre de sesión con y sin votación activa.

### Votación

- falta de sesión;
- falta de quórum;
- mayoría simple;
- mayoría especial sobre presentes;
- mayoría especial sobre cuerpo;
- voto duplicado;
- cambio de presencia durante votación;
- cierre automático;
- cierre forzado;
- empate y desempate;
- votación inconclusa.

### Frontend

- carga inicial sin backend;
- reconexión;
- sin sesión;
- recinto preparado;
- sesión abierta;
- votación en curso;
- ocultamiento y aparición de votos;
- cierre y limpieza visual;
- cola de palabra larga;
- crecimiento de eventos sin alterar el grid;
- consola del navegador sin excepciones.

### Hardware

- identificación persistente del dispositivo;
- envío del identificador lógico correcto;
- una sola pulsación por evento físico;
- reconexión del backend;
- comportamiento Linux y Windows si el cambio afecta código compartido.

## 8. Datos de prueba

No reemplazar los archivos institucionales con datos ficticios dentro de una tarea normal. Para pruebas locales:

- usar una copia temporal fuera del repositorio; o
- crear fixtures claramente ficticios en una carpeta de pruebas cuando exista una tarea específica para incorporar testing.

Nunca publicar DNI, mapeos físicos, secretos o registros reales nuevos.

## 9. Entrega

Registrar en la Pull Request:

```text
Validación ejecutada:
- [comando o recorrido]
- resultado

No validado:
- [aspecto y motivo]
```

No usar frases genéricas como “probado” o “funciona” sin detallar el recorrido.
