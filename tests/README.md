# Pruebas de caracterizacion

Ejecutar desde la raiz del repositorio, luego de instalar `requirements-backend.txt`:

```powershell
python -m pytest -q
python -m pytest -q tests/unit
python -m pytest -q tests/integration
python -m pytest -q --strict-markers --cov=app --cov-report=term-missing --cov-report=xml
```

Las fixtures aislan los singletons de sesion, votacion y pantallas, los IDs en memoria y el buffer de logs. Los concejales usados por las pruebas son ficticios y los logs se escriben en directorios temporales de pytest.

El workflow `Backend CI` ejecuta la suite para Pull Requests y cambios incorporados a `v2`. La cobertura de `app` es informativa y no tiene un umbral mínimo todavía.
