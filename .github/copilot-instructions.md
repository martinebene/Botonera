# Instrucciones para GitHub Copilot

Seguir `AGENTS.md` como fuente canónica para todo el repositorio.

Antes de proponer cambios:

- verificar que la rama no sea `main`;
- leer `README.md` y los documentos de `docs/agents/` relevantes;
- identificar archivos propietarios y consumidores del contrato;
- mantener el alcance quirúrgico;
- preservar rutas, JSON, IDs HTML, polling y comportamiento de otras pantallas salvo pedido explícito.

No sugerir ni aplicar automáticamente:

- migraciones de arquitectura;
- nuevas dependencias;
- cambios de infraestructura o despliegue;
- renombrados masivos;
- eliminación de `/pantalla` o `/pantalla2`;
- cambios de reglas de votación sin casos acordados;
- datos reales, secretos, logs o mapeos físicos.

No existe una suite automatizada completa. Toda Pull Request debe detallar la validación ejecutada según `docs/agents/DEVELOPMENT.md` y declarar lo no verificado.
