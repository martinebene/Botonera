## Objetivo

<!-- Qué problema resuelve esta Pull Request. -->

## Alcance

<!-- Qué se modificó y qué quedó expresamente fuera. -->

## Archivos principales

<!-- Enumerar archivos y responsabilidad del cambio. -->

## Comportamiento

**Antes:**

**Después:**

## Contratos

- [ ] No cambia rutas ni cuerpos JSON.
- [ ] No cambia la forma del estado consumido por frontends.
- [ ] No cambia IDs HTML, polling ni otras pantallas.
- [ ] No cambia reglas de sesión, quórum o votación.
- [ ] Si cambia alguno de los anteriores, está explicado y se validaron todos los consumidores.

## Validación ejecutada

<!-- Detallar comandos y recorridos concretos; no escribir solo “probado”. -->

```text
python -m compileall app devices_services
```

- [ ] Backend inicia desde la raíz del repositorio.
- [ ] Endpoints afectados verificados.
- [ ] Recorrido funcional afectado verificado.
- [ ] Frontend afectado revisado en navegador.
- [ ] Consola del navegador sin errores nuevos.
- [ ] Logs revisados.

## No validado

<!-- Aspectos que no pudieron verificarse y motivo. -->

## Riesgos y compatibilidad

- [ ] No incorpora secretos ni datos personales reales.
- [ ] No agrega logs, caches, entornos virtuales ni archivos generados.
- [ ] No modifica `main` ni configura despliegue.
- [ ] Dependencias nuevas justificadas, si existen.
- [ ] Compatibilidad Linux/Windows evaluada cuando corresponde.

## Evidencia

<!-- Capturas, respuestas JSON anonimizadas, logs de prueba o pasos reproducibles. -->
