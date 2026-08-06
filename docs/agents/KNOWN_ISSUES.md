# Observaciones e inconsistencias conocidas

Estas observaciones describen el estado encontrado en `v2`. No son una lista de tareas autorizadas. Un agente debe corregirlas únicamente cuando el alcance lo indique expresamente.

## 1. Producción y desarrollo

- `main` es la referencia de producción.
- `v2` está por delante de `main` y contiene una refactorización todavía incompleta.
- No asumir que todo comportamiento de `v2` ya fue validado en sesión real.

## 2. Estado en memoria y procesos

`SesionService`, `VotacionService` e `InfoPantallasService` son singletons de módulo. Cada proceso Python mantiene su propia copia.

Consecuencia: una configuración con varios workers puede producir estados diferentes entre requests atendidos por procesos distintos. No aumentar workers ni afirmar compatibilidad multiproceso sin resolver explícitamente la persistencia o coordinación del estado.

## 3. Configuración y directorio de trabajo

`settings = Settings()` se ejecuta durante la importación y requiere `config.json`. Varias rutas son relativas:

- `config.json`;
- `data/concejales.csv`;
- `logs/`;
- directorios estáticos.

Iniciar la aplicación desde otro directorio puede fallar. No transformar rutas o empaquetado como parte lateral de otra tarea.

## 4. Flujo preparar/abrir sesión

El backend separa:

1. `preparar_sesion`;
2. `abrir_sesion`.

La interfaz de moderación revisada llama a `abrir_sesion`, pero no se observó en su flujo principal un control equivalente para preparar el recinto. Verificar el recorrido real antes de modificar cualquiera de las dos capas.

## 5. Documentación del mapa de teclas

El manual de usuario contiene un mapa anterior. La implementación actual de `app/services/input_service.py` usa:

- `1`: positivo;
- `2`: abstención;
- `3`: negativo;
- `7`: uso de la palabra;
- `8`: test visual;
- `9`: presencia.

No usar el manual como única fuente para modificar entradas. Si una tarea cambia el mapa, actualizar en conjunto código, emulador, servicio físico, manual y pruebas.

## 6. Formato del orden del día

Hay deriva documental:

- `README.md` y el manual describen en partes un CSV separado por coma y estilo RFC4180;
- el código actual de moderación define un encabezado separado por punto y coma y divide cada línea con `split(";")`;
- los archivos de ejemplo deben considerarse evidencia adicional del uso actual.

No “normalizar” formato, separador o tolerancia sin una decisión funcional explícita y una estrategia de compatibilidad.

## 7. Pantalla y Pantalla 2

Existen dos implementaciones públicas:

- `/pantalla`: consume `/estados/estado_global`;
- `/pantalla2`: consume `/estados/info_pantallas` y `/estados/configuracion`.

También hay dos monitores técnicos. Esto representa una migración o comparación en curso, no duplicación accidental demostrada.

## 8. Proyección `InfoPantallas`

La clase y el frontend nuevo no están totalmente alineados en todos los campos declarados o esperados. Por ejemplo, el frontend normaliza `eventos`, mientras la serialización revisada no los entrega. Otros atributos existen en la clase pero no necesariamente aparecen en `to_dict()`.

Antes de cambiar la proyección:

- enumerar campos producidos;
- enumerar campos consumidos por `pantalla2` y el monitor;
- definir compatibilidad con valores ausentes;
- validar el recorrido visual completo.

## 9. Serialización de sesión

`Sesion.to_dict()` devuelve `en_uso_de_palabra` como referencia de objeto, mientras la cola se transforma con `to_dict()`. FastAPI puede intentar codificar el objeto, pero el contrato no es tan explícito como el resto.

No cambiarlo sin comprobar qué forma reciben actualmente moderación y pantalla.

## 10. Ausencia de pruebas automatizadas

No se encontró una suite de `pytest`, `unittest` ni CI de validación. La seguridad de los cambios depende hoy de pruebas manuales y compilación.

Agregar testing es deseable, pero debe hacerse incrementalmente y sin reescribir el sistema solo para facilitar pruebas.

## 11. Archivos históricos y generados

La historia contiene caches Python eliminados y el repositorio conserva registros históricos en `logs/`, aunque `.gitignore` excluye logs nuevos. No volver a incorporar caches, entornos virtuales o logs de ejecución.

La eliminación o depuración de archivos históricos requiere una tarea separada, especialmente si son evidencia operativa.

## 12. Dependencias

`requirements-backend.txt` fija versiones e incluye paquetes que podrían no estar usados todavía, como SQLAlchemy. No eliminar dependencias por inspección superficial ni agregar otras sin verificar producción.

El servicio de teclados tiene su propio `requirements.txt` y debe conservar esa separación.

## 13. Reglas de mayoría

Las reglas están implementadas entre `Votacion.cerrar()` y `VotacionService`. Cualquier cambio puede afectar:

- mayoría simple;
- mayoría especial;
- cálculo sobre presentes o cuerpo;
- abstenciones;
- falta de quórum;
- voto pendiente;
- empate y desempate.

No modificar una fórmula sin casos numéricos acordados y pruebas para cada variante.

## 14. Nombres y estilo en transición

Hay nombres como `InfoPantallas.py` y `InfoPantallasService.py` que no siguen el estilo habitual de módulos Python, además de comentarios y código histórico. No hacer renombrados cosméticos porque afectan imports y despliegue en sistemas sensibles a mayúsculas.

## 15. Seguridad y alcance institucional

El repositorio es público, aunque la documentación lo describe como institucional privado. Evitar incorporar:

- credenciales;
- direcciones internas sensibles;
- datos personales reales adicionales;
- mapeos físicos de dispositivos;
- registros de sesiones no anonimizados;
- procedimientos operativos sensibles no necesarios para desarrollo.
