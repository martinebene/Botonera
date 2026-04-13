# 📘 MANUAL DE USUARIO -- SISTEMA BOTONERA

## Gestión de Sesiones, Votación Electrónica y Orden del Día

------------------------------------------------------------------------

# 1️⃣ INTRODUCCIÓN

Este manual describe en detalle el funcionamiento del sistema BOTONERA
según el rol del usuario y el estado de la sesión.

Roles contemplados:

-   🧑‍💼 Administrador de Sesión
-   🧑‍⚖️ Concejal

------------------------------------------------------------------------

# 2️⃣ ORDEN DEL DÍA (Carga CSV)

El Orden del Día permite precargar votaciones para agilizar la sesión.

## 2.1 Ubicación

Pantalla **Moderación → Cuadrante Q2 → "Orden del día"**

Botones disponibles:

-   **Cargar CSV**
-   **Limpiar**

------------------------------------------------------------------------

## 2.2 Formato Obligatorio del Archivo CSV

El archivo debe cumplir estrictamente:

### ✔ Header EXACTO (sin espacios adicionales):

    nro_votacion,tipo,tema,factor_de_mayoria,respecto

### ✔ Reglas:

-   Separador: coma (,)
-   Permite comillas dobles para campos con comas (formato RFC4180)
-   No se permiten columnas adicionales
-   No se permiten columnas faltantes

------------------------------------------------------------------------

## 2.3 Descripción de Columnas

### 🔢 nro_votacion

Número entero. Ejemplo: `37`

### 📄 tipo

Valores válidos (no sensible a mayúsculas):

-   Despacho
-   Mocion
-   Sobre tabla
-   Ratificacion

### 📝 tema

Texto libre. Si contiene comas debe ir entre comillas:

    "Tratamiento de presupuesto 2026, segunda lectura"

### 📊 factor_de_mayoria

-   Vacío o 0 → mayoría simple
-   Decimal con punto (0.66, 1, 1.0)
-   NO usar coma decimal
-   NO usar símbolo %

### 🧮 respecto

-   presentes
-   cuerpo (No sensible a mayúsculas)

------------------------------------------------------------------------

## 2.4 Validación

Si el CSV es inválido:

-   Se rechaza COMPLETO
-   La tabla queda vacía
-   No se carga parcialmente

------------------------------------------------------------------------

## 2.5 Uso Operativo

1.  Presionar **Cargar CSV**
2.  Seleccionar archivo
3.  Verificar tabla cargada
4.  Hacer click en una fila para copiar datos a Q1
5.  Abrir votación normalmente

------------------------------------------------------------------------

# 3️⃣ ROL: CONCEJAL

El comportamiento depende del estado de la sesión.

------------------------------------------------------------------------

# 3.1 Estado: SESIÓN CERRADA

Situación: - No hay sesión activa.

El concejal puede:

-   ❌ No puede votar
-   ❌ No puede solicitar uso de la palabra
-   ❌ No puede modificar presencia

El sistema ignora entradas de teclado.

------------------------------------------------------------------------

# 3.2 Estado: SESIÓN ABIERTA -- SIN VOTACIÓN

Situación: - Sesión abierta - No hay votación en curso

El concejal puede:

-   ✔ Marcar presencia / ausencia
-   ✔ Solicitar uso de la palabra
-   ✔ Ver quórum en pantalla
-   ❌ No puede votar (no hay votación abierta)

------------------------------------------------------------------------

# 3.3 Estado: SESIÓN ABIERTA -- VOTACIÓN EN CURSO

Situación: - Sesión abierta - Votación activa

El concejal puede:

-   ✔ Emitir voto (Positivo / Negativo / Abstención)
-   ✔ Ver estado en tiempo real
-   ✔ Cambiar presencia (si reglamento lo permite)

Restricciones:

-   ❌ No puede votar más de una vez
-   ❌ No puede cambiar voto una vez registrado
-   ❌ No puede solicitar uso de palabra si reglamento lo bloquea

------------------------------------------------------------------------

# 3.4 Estado: VOTACIÓN EMPATADA

Situación: - Votación cerrada con empate

El concejal común:

-   ❌ No puede volver a votar

Administrador:

-   ✔ Ejecuta voto desempate

------------------------------------------------------------------------

# 4️⃣ EMISIÓN DE VOTO (Teclado)

Ejemplo típico de mapeo:

-   Tecla 1 → Positivo
-   Tecla 2 → Negativo
-   Tecla 3 → Abstención
-   Tecla 7 → Alternar presencia

El voto queda registrado inmediatamente y se refleja en pantalla
recinto.

------------------------------------------------------------------------0

# 5️⃣ PANTALLA RECINTO

Muestra en tiempo real:

-   Resumen de votación
-   Tema
-   Estado (En curso, Aprobada, Rechazada, Empatada)
-   Plano del recinto
-   Uso de la palabra
-   Eventos principales

Se actualiza automáticamente cada \~300ms.

------------------------------------------------------------------------

# 6️⃣ REGLAS GENERALES DEL SISTEMA

-   Solo una sesión activa
-   Solo una votación activa
-   Cierre automático si votan todos los presentes
-   Soporte para mayoría simple y especial
-   Registro completo de eventos

------------------------------------------------------------------------

# 7️⃣ BUENAS PRÁCTICAS PARA USO EN SESIÓN

-   Verificar quórum antes de abrir votación
-   Confirmar parámetros de mayoría
-   Validar tema antes de abrir votación
-   Supervisar consola de eventos ante cualquier anomalía

------------------------------------------------------------------------

Manual técnico-operativo para uso institucional.
